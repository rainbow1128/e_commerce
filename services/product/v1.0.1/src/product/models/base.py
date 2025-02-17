import enum
import operator
from functools import partial, reduce

from MySQLdb.constants.ER import BAD_NULL_ERROR, DUP_ENTRY

from django.db import models, connections as db_conns_map
from django.db.utils import IntegrityError
from django.db.models.fields.related import RelatedField
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from ecommerce_common.models.enums.django import UnitOfMeasurement, TupleChoicesMeta
from ecommerce_common.models.mixins import MinimumInfoMixin, IdGapNumberFinder
from ecommerce_common.models.closure_table import ClosureTableModelMixin
from softdelete.models import SoftDeleteObjectMixin

from .common import (
    ProductmgtChangeSet,
    ProductmgtSoftDeleteRecord,
    _BaseIngredientManager,
    _BaseIngredientQuerySet,
    BaseProductIngredient,
    _UserProfileMixin,
    DB_ALIAS_APPLIED,
    _atomicity_fn,
    _MatCodeOptions,
)

from .fields import CompoundPrimaryKeyField

# The term "product" here means :
# * items for sale (saleable)
# * items bought from suppliers, and then used as material of your product (non-saleable)


def mysql_extract_dup_id_from_error(error):
    # MySQL database reports each error for only one single duplicate primary
    # key, if bulk-create operation from application has more than one duplicate
    # primary key, MySQL still reports duplicate key error one by one instead of
    # gathering all duplicate pk values in one single error,
    # which is not very efficient.
    words = error.args[1].split(" ")
    dup_id = words[2]
    if not dup_id[0].isdigit():
        dup_id = dup_id[1:-1]
    return int(dup_id)


class AppIdGapNumberFinder(IdGapNumberFinder):
    def expected_db_errors(self):
        return (IntegrityError,)

    def is_db_err_recoverable(self, error):
        # currently the following condition is MySQL-specific (TODO)
        def mysql_pk_dup_error(x):
            return x.args[0] == DUP_ENTRY and "PRIMARY" in x.args[1]

        recoverable = (
            error.args[0] == BAD_NULL_ERROR and "id" in error.args[1]
        ) or mysql_pk_dup_error(error)
        return recoverable

    def low_lvl_get_gap_range(self, raw_sql_queries) -> list:
        out = []
        db_conn = db_conns_map[DB_ALIAS_APPLIED]
        # currently this service does not enable multi-statement capability flag in MariaDB
        # connection arguments, the 3 raw-SQL queries have to be executed one after another in
        # different network flights
        with db_conn.cursor() as cursor:  # the connection has to be DB-API 2.0 compliant
            cursor.execute(raw_sql_queries[0])
            row = cursor.fetchone()
            if row:
                out.append(row)
            # cursor.nextset() should be `None`, means no more result set
            cursor.execute(raw_sql_queries[1])
            rows = cursor.fetchall()
            out.extend(rows)
            # cursor.nextset()
            cursor.execute(raw_sql_queries[2])
            row = cursor.fetchone()
            if row:
                out.append(row)
        return out

    def get_pk_db_column(self, model_cls) -> str:
        id_field_name = "id"
        deferred_attr = getattr(model_cls, id_field_name, None)
        pk_field = deferred_attr.field
        return pk_field.db_column or pk_field.name

    def get_db_table_name(self, model_cls) -> str:
        return model_cls._meta.db_table

    def extract_dup_id_from_error(self, error):
        return mysql_extract_dup_id_from_error(error)


class UniqueIdentifierMixin(models.Model):
    """
    the mixin provides 4-byte integer as primary key, key generating function,
    collision handling function on insertion/update to guarantee uniqueness.
    * The id field in this mixin does NOT use auto-increment feature supported by
      supported low-level databases.
    * Also the id does NOT use any UUID-like generator because the probability of
      collision is not exactly zero even you use something like UUID4,
      and you still need to handle collision when the database table grows
      to very large extent. (not to mention UUID is 16 bytes requires 4x space
      than a typical 4-byte integer-based B-tree index)
    """

    class Meta:
        abstract = True

    id = models.PositiveIntegerField(
        primary_key=True, unique=True, db_index=True, db_column="id"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._id_gap_finder = AppIdGapNumberFinder(orm_model_class=type(self))

    def save(self, *args, **kwargs):
        save_instance_fn = partial(super().save, *args, **kwargs)
        return self._id_gap_finder.save_with_rand_id(save_instance_fn, objs=[self])


## end of class UniqueIdentifierMixin


class _TagQuerySet(models.QuerySet):
    def get_ascs_descs_id(
        self, IDs, fetch_asc=True, fetch_desc=True, depth=None, self_exclude=True
    ):
        assert (
            fetch_asc or fetch_desc
        ), "either fetch_asc or fetch_desc must be enabled, but not both"
        is_depth_int = depth is not None and (
            isinstance(depth, int)
            or (isinstance(depth, str) and depth.lstrip("-").isdigit())
        )
        init_qset = self.model.objects.all()
        if "root" in IDs:
            depth = int(depth) if is_depth_int and not fetch_asc else 0
            qset = init_qset.annotate(asc_cnt=models.Count("ancestors"))
            qset = qset.filter(asc_cnt=1).values_list("pk", flat=True)
            depth_range = models.Q(descendants__ancestor__in=qset) & models.Q(
                descendants__depth__lte=depth
            )
            qset = (
                init_qset.distinct()
                .filter(depth_range)
                .values_list("descendants__descendant", flat=True)
            )
            final_cond = models.Q(id__in=qset)
        else:
            DEPTH_UNLIMITED = -1
            depth = int(depth) if is_depth_int is True else 1
            ids_qset = init_qset.filter(id__in=IDs).values_list("pk", flat=True)
            aug_IDs = []
            if fetch_desc:
                depth_desc_range = models.Q(descendants__ancestor__in=ids_qset)
                if self_exclude:
                    depth_desc_range = depth_desc_range & models.Q(
                        descendants__depth__gt=0
                    )
                if depth > DEPTH_UNLIMITED:
                    depth_desc_range = depth_desc_range & models.Q(
                        descendants__depth__lte=depth
                    )
                qset = (
                    init_qset.distinct()
                    .filter(depth_desc_range)
                    .values_list("descendants__descendant", flat=True)
                )
                aug_IDs.append(models.Q(id__in=qset))
            if fetch_asc:
                depth_asc_range = models.Q(ancestors__descendant__in=ids_qset)
                if self_exclude:
                    depth_asc_range = depth_asc_range & models.Q(ancestors__depth__gt=0)
                if depth > DEPTH_UNLIMITED:
                    depth_asc_range = depth_asc_range & models.Q(
                        ancestors__depth__lte=depth
                    )
                qset = (
                    init_qset.distinct()
                    .filter(depth_asc_range)
                    .values_list("ancestors__ancestor", flat=True)
                )
                aug_IDs.append(models.Q(id__in=qset))
            final_cond = reduce(operator.or_, aug_IDs)
        aug_ids_qset = init_qset.filter(final_cond).values_list("id", flat=True)
        return aug_ids_qset

    def delete(self, *args, **kwargs):
        if not hasattr(self, "_descs_deletion_included"):
            descs_id = self.values_list("descendants__descendant__pk", flat=True)
            manager = self.model.objects
            rec_qs = manager.filter(pk__in=descs_id)
            rec_qs._descs_deletion_included = True
            rec_qs.delete()
        else:
            super().delete(*args, **kwargs)


## end of class _TagQuerySet


class _TagManager(models.Manager):
    def all(self, *args, **kwargs):
        qset = super().all(*args, **kwargs)
        qset.__class__ = _TagQuerySet
        return qset

    def filter(self, *args, **kwargs):
        qset = super().filter(*args, **kwargs)
        qset.__class__ = _TagQuerySet
        return qset

    def annotate(self, *args, **kwargs):
        qset = super().annotate(*args, **kwargs)
        qset.__class__ = _TagQuerySet
        return qset

    def order_by(self, *field_names):
        qset = super().order_by(*field_names)
        qset.__class__ = _TagQuerySet
        return qset

    def only(self, *fields):
        qset = super().only(*fields)
        qset.__class__ = _TagQuerySet
        return qset

    def defer(self, *fields):
        qset = super().defer(*fields)
        qset.__class__ = _TagQuerySet
        return qset

    def reverse(self):
        qset = super().reverse()
        qset.__class__ = _TagQuerySet
        return qset


class ProductTag(_UserProfileMixin, MinimumInfoMixin):
    """
    hierarchical tags for product categories
    """

    class Meta:
        db_table = "product_tag"

    objects = _TagManager()
    min_info_field_names = ["id", "name"]
    name = models.CharField(max_length=64, unique=False)

    def delete(self, *args, **kwargs):
        descs_id = self.descendants.values_list("descendant__id", flat=True)
        qset = type(self).objects.filter(pk__in=descs_id)
        qset._descs_deletion_included = True
        qset.delete()


class ProductTagClosure(ClosureTableModelMixin):
    """closure table to represent tree structure of tag hierarchy"""

    class Meta(ClosureTableModelMixin.Meta):
        db_table = "product_tag_closure"

    ancestor = ClosureTableModelMixin.asc_field(ref_cls=ProductTag)
    descendant = ClosureTableModelMixin.desc_field(ref_cls=ProductTag)


class _RelatedFieldMixin:
    """
    allow to change related_name for related field (e.g. foreign key, m2m key)
    at runtime
    """

    @classmethod
    def set_related_name(cls, field_name, value):
        valid_list = (
            ForwardManyToOneDescriptor,
            ManyToManyDescriptor,
        )
        related_descriptor = getattr(cls, field_name, None)
        assert related_descriptor and isinstance(related_descriptor, valid_list), (
            "related_descriptor inproper type : %s" % related_descriptor
        )

        related_field = related_descriptor.field  # has to be RelatedField
        assert related_field and isinstance(related_field, RelatedField), (
            "related_field should be RelatedField, but it is %s" % related_field
        )
        # There seems to be inconsistency in the Django ORM when you need to modify
        # `related_name` of a RelatedField inherited from abstract parent model.
        # The code below isn't perfect solution, because the related model of a
        # RelatedField still adds reverse relationship attribute  with default
        # `related_name` (e.g. `<YOUR_MODEL_NAME>_set`) ...
        related_field.remote_field.related_name = (
            value  # removal will cause new migration
        )
        # related_field.contribute_to_class(cls=cls, name=value) # why this cause errors in makemigrations
        related_model = related_field.remote_field.model
        # With default `related_name` , it is extremely difficult to find out where in
        # the code does Django ORM add reverse relationship attribute to the related model
        # of a RelatedField (e.g. fk or m2m field) in a model.
        # The hacky workaround below looks for relation attribute in the related model
        # by default `related_name` value , then modify the key of the attribute. That
        # means this function can be executed only once for each RelatedField in a
        # concrete model at runtime.
        default_related_name = "%s_set" % cls._meta.model_name
        assert hasattr(related_model, default_related_name), (
            "the related_name of the related model `%s` has been modified to non-default value  since application started"
            % (related_model)
        )

        rev_rel_descriptor = getattr(related_model, default_related_name)
        assert (
            related_field is rev_rel_descriptor.field
        ), "both of them have to be the same object"

        delattr(related_model, default_related_name)
        setattr(related_model, value, rev_rel_descriptor)


## end of  _RelatedFieldMixin


class _SaleableItemQuerySet(_BaseIngredientQuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        save_instance_fn = partial(super().bulk_create, objs, *args, **kwargs)
        if not hasattr(self, "_id_gap_finder"):
            self._id_gap_finder = AppIdGapNumberFinder(orm_model_class=self.model)
        return self._id_gap_finder.save_with_rand_id(save_instance_fn, objs=objs)


class _SaleableItemManager(_BaseIngredientManager):
    default_qset_cls = _SaleableItemQuerySet


class AbstractProduct(
    BaseProductIngredient,
    UniqueIdentifierMixin,
    _UserProfileMixin,
    _RelatedFieldMixin,
    MinimumInfoMixin,
):
    """
    Define abstract product model, it records generic product information that is required.
    this abstract class (model) can be inherited if user wants to :
    * sell product item individually
    * or define packages that sell several product items togather at once (Package)
    """

    class Meta:
        abstract = True

    objects = _SaleableItemManager()
    # one product item could have many tags, a tag includes several product items
    tags = models.ManyToManyField(
        ProductTag,
        db_column="tags",
    )
    # global visible flag at front store (will be used at PoS service)
    visible = models.BooleanField(default=False)
    # current price of this product or package item. this field value also means the base price
    # without discount and extra charge due to customization
    price = models.FloatField(default=0.00)
    # TODO, does this project require secondary index on `profile` column ?
    min_info_field_names = ["id", "name"]

    @_atomicity_fn()
    def delete(self, *args, **kwargs):
        hard_delete = kwargs.get("hard", False)
        super().delete(*args, **kwargs)
        if not hard_delete:
            self.tags.clear()  # still hard-delete rows in m2m relation table, not tag table itself

    ## end of delete()


class ProductSaleableItem(AbstractProduct):
    quota_material = _MatCodeOptions.MAX_NUM_SALE_ITEMS

    class Meta(AbstractProduct.Meta):
        db_table = "product_saleable_item"

    unit = models.SmallIntegerField(
        blank=False, null=False, choices=UnitOfMeasurement.choices
    )

    @_atomicity_fn()
    def delete(self, *args, **kwargs):
        hard_delete = kwargs.get("hard", False)
        if not hard_delete:  # let nested fields add in the same soft-deleted changeset
            if kwargs.get("changeset", None) is None:
                profile_id = kwargs["profile_id"]  # kwargs.get('profile_id')
                kwargs["changeset"] = self.determine_change_set(profile_id=profile_id)
        deleted = super().delete(*args, **kwargs)
        if not hard_delete:
            self.ingredients_applied.all().delete(*args, **kwargs)
            self.pkgs_applied.all().delete(*args, **kwargs)
            kwargs.pop("changeset", None)
        return deleted


class ProductSaleablePackage(AbstractProduct):
    quota_material = _MatCodeOptions.MAX_NUM_SALE_PKGS

    class Meta(AbstractProduct.Meta):
        db_table = "product_saleable_package"

    @_atomicity_fn()
    def delete(self, *args, **kwargs):
        hard_delete = kwargs.get("hard", False)
        if not hard_delete:  # let nested fields add in the same soft-deleted changeset
            if kwargs.get("changeset", None) is None:
                profile_id = kwargs["profile_id"]  # kwargs.get('profile_id')
                kwargs["changeset"] = self.determine_change_set(profile_id=profile_id)
        deleted = super().delete(*args, **kwargs)
        if not hard_delete:
            self.saleitems_applied.all().delete(*args, **kwargs)
            kwargs.pop("changeset", None)
        return deleted


ProductSaleableItem.set_related_name(field_name="tags", value="tagged_products")
ProductSaleablePackage.set_related_name(field_name="tags", value="tagged_packages")


class ProductSaleableItemComposite(SoftDeleteObjectMixin):
    """
    This model is used in case user's business details development or manufacturing
    of all the saleable items with all required ingredients.
    Each instance of this model indicates one ingredient type applied to developing
    a saleable item with number of (or amount of, if uncountable) the ingredients to use.
    """

    # TODO, add another model for recording instructions of saleable item manufacturing
    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord

    class Meta:
        db_table = "product_saleable_item_composite"

    quantity = models.FloatField(blank=False, null=False)
    # Different saleable items may require the same ingredient in different volume,
    # it would be appropriate to let end-users configure the amount of ingredient when
    # they develop recipe of each saleable item (if they produce the items by themselves).
    unit = models.SmallIntegerField(
        blank=False, null=False, choices=UnitOfMeasurement.choices
    )
    ingredient = models.ForeignKey(
        "ProductDevIngredient",
        on_delete=models.CASCADE,
        db_column="ingredient",
        related_name="saleitems_applied",
    )
    sale_item = models.ForeignKey(
        "ProductSaleableItem",
        on_delete=models.CASCADE,
        db_column="sale_item",
        related_name="ingredients_applied",
    )
    id = CompoundPrimaryKeyField(inc_fields=["sale_item", "ingredient"])


class ProductSaleablePackageComposite(SoftDeleteObjectMixin):
    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord

    class Meta:
        db_table = "product_saleable_package_composite"

    quantity = models.FloatField(blank=False, null=False)
    unit = models.SmallIntegerField(
        blank=False, null=False, choices=UnitOfMeasurement.choices
    )
    sale_item = models.ForeignKey(
        "ProductSaleableItem",
        on_delete=models.CASCADE,
        db_column="sale_item",
        related_name="pkgs_applied",
    )
    package = models.ForeignKey(
        "ProductSaleablePackage",
        on_delete=models.CASCADE,
        db_column="package",
        related_name="saleitems_applied",
    )
    id = CompoundPrimaryKeyField(inc_fields=["sale_item", "package"])


class ProductSaleableItemMedia(SoftDeleteObjectMixin):
    """
    media file paths e.g. image / audio / video for saleable item(s)
    """

    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord

    class Meta:
        db_table = "product_saleable_item_media"

    sale_item = models.ForeignKey(
        "ProductSaleableItem",
        on_delete=models.CASCADE,
        db_column="sale_item",
        related_name="media_set",
    )
    # currently the file-uploading application supports only image or video file as
    # media associated with each saleable item, this `media` field records identifier
    # to specific file stored in file-uploading application
    media = models.CharField(max_length=42, unique=False)


class ProductSaleablePackageMedia(SoftDeleteObjectMixin):
    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord

    class Meta:
        db_table = "product_saleable_package_media"

    sale_pkg = models.ForeignKey(
        "ProductSaleablePackage",
        on_delete=models.CASCADE,
        db_column="sale_pkg",
        related_name="media_set",
    )
    media = models.CharField(max_length=42, unique=False)


class RelatedFieldChoicesMeta(TupleChoicesMeta):
    @property
    def related_field_name(cls):
        _map = {member.name: member.value[0][1] for member in cls}
        _attributes = _map
        _map_cls = type("_map_cls", (), _attributes)
        return _map_cls

    def related_field_map(cls, dtype_code):
        _map = {member.value[0][0]: member.value[0][1] for member in cls}
        return _map.get(dtype_code, None)


class _ProductAttrValueDataType(tuple, enum.Enum, metaclass=RelatedFieldChoicesMeta):
    """
    data type options for textual/numeric attributes of saleable item(s)
    """

    STRING = ((1, "attr_val_str"),)
    INTEGER = ((2, "attr_val_int"),)
    POSITIVE_INTEGER = ((3, "attr_val_pos_int"),)
    FLOAT = ((4, "attr_val_float"),)
    # TODO: figure out why dict choices is not possible , is it unhashable ??
    # STRING           = {'choice': 1, 'related_field':'attr_val_str'    },
    # INTEGER          = {'choice': 2, 'related_field':'attr_val_int'    },
    # POSITIVE_INTEGER = {'choice': 3, 'related_field':'attr_val_pos_int'},
    # FLOAT            = {'choice': 4, 'related_field':'attr_val_float'  },


class ProductAttributeType(SoftDeleteObjectMixin, MinimumInfoMixin):
    """
    this is EAV pattern, a schemaless design,
    in order to avoid mistakes that might be made by users :
    * this attribute table (and the value table below) should be edited carefully
      only by authorized staff (better not letting customers add whatever attribute
      they want), in order to avoid duplicate attribute types with the same semantic.
    * each attribute may require different data type as the attribute value, so
      I create abstract model class `BaseProductAttributeValue` for all attribute
      values tied to existing attribute type, and existing product item, then subclass it
      for different data types.
    * each attribute type added in this table are optional to all product items, product
      owners or managers are free to determine what attribute types they'll apply to
      each of their product.
    * To mitigate performance degradation when performing query with complex condition
      in such schemaless design, application frontend can preload all required attribute
      types in advance, let end users at frontend select attribute types, then use id
      of each attribute type on sending search request (instead of using name of each
      attribute type). By doing so the database (at backend) does not have to join this
      table when searching for attributes and their values
    """

    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord
    min_info_field_names = ["id", "name", "dtype"]

    class Meta:
        db_table = "product_attribute_type"

    # help text to describe how this attribute is used to a product
    name = models.CharField(max_length=64, unique=False, blank=False)
    # data type of the attribute value, to convert to reverse field, you need _ProductAttrValueDataType.related_field_name
    dtype = models.SmallIntegerField(choices=_ProductAttrValueDataType.choices)

    @property
    def attr_val_set(self):
        related_field_name = _ProductAttrValueDataType.related_field_map(
            dtype_code=self.dtype
        )
        if related_field_name:
            return getattr(self, related_field_name)


class BaseProductAttributeValue(SoftDeleteObjectMixin, _RelatedFieldMixin):
    """
    user-defined metadata for storing textual/numeric attributes applied to saleable items.

    Here are examples of how attribiute key/value pairs may look like :
    * paths of (different qualities of) image / audio / video sample file, for showcasing this product
    * weight, physical size e.g. width x depth x height per unit
    * there should be unit of measure for both countable items (e.g. number of cans, bottles)
      and uncountable items (e.g. litre, gallon, square-meter)
    * the metadata format can be XML / JSON / CSV, or user-defined data structure
    """

    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord
    DATATYPE = None

    class Meta:
        abstract = True

    allowed_models = (
        models.Q(app_label="product", model="ProductSaleableItem")
        | models.Q(app_label="product", model="ProductSaleablePackage")
        | models.Q(app_label="product", model="ProductDevIngredient")
    )
    ingredient_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        null=False,
        db_column="ingredient_type",
        limit_choices_to=allowed_models,
    )
    ingredient_id = models.PositiveIntegerField(db_column="ingredient_id")
    ingredient_ref = GenericForeignKey(
        ct_field="ingredient_type", fk_field="ingredient_id"
    )
    attr_type = models.ForeignKey(
        ProductAttributeType, db_column="attr_type", on_delete=models.CASCADE
    )
    _extra_charge = GenericRelation(
        "ProductAppliedAttributePrice",
        object_id_field="attrval_id",
        content_type_field="attrval_type",
    )

    def __init__(self, *args, extra_amount=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._extra_amount = extra_amount

    @property
    def extra_amount(self):
        return self._extra_amount or self.extra_charge

    @extra_amount.setter
    def extra_amount(self, value):
        self._extra_amount = value

    @property
    def extra_charge(self):
        qset = self._extra_charge.all(with_deleted=self.is_deleted())
        if qset.exists():  # suppose to be only one instance that represents price
            return qset.first().amount

    @_atomicity_fn()
    def save(self, *args, **kwargs):
        out = super().save(*args, **kwargs)
        if self.extra_amount is not None and self.extra_amount > 0.0:
            # self.refresh_from_db(fields=['pk']) # auto fetch ID at model level
            qset = self._extra_charge.all(with_deleted=self.is_deleted())
            obj = qset.first()
            if not obj:
                obj = self._extra_charge.model()
                obj.attrval_type = ContentType.objects.get_for_model(self)
                obj.attrval_id = self.pk
            if obj.amount != self.extra_amount:
                obj.amount = self.extra_amount
                obj.save()
            # set() cannot handle unsaved instances, doesn't seem to work for foreign key
            # self._extra_charge.set([obj], clear=True)
        return out

    @_atomicity_fn()
    def delete(self, *args, **kwargs):
        hard_delete = kwargs.get("hard", False)
        if not hard_delete:
            if kwargs.get("changeset", None) is None:
                profile_id = kwargs["profile_id"]
                kwargs["changeset"] = self.determine_change_set(profile_id=profile_id)
        SoftDeleteObjectMixin.delete(self, *args, **kwargs)
        if not hard_delete:
            self._extra_charge.all().delete(*args, **kwargs)
            kwargs.pop("changeset", None)
            kwargs.pop("profile_id", None)

    ## end of delete()


## end of class BaseProductAttributeValue


class ProductAttributeValueStr(BaseProductAttributeValue):
    class Meta:
        db_table = "product_attribute_value_str"

    value = models.CharField(max_length=64, unique=False)
    DATATYPE = _ProductAttrValueDataType.STRING


class ProductAttributeValuePosInt(BaseProductAttributeValue):
    class Meta:
        db_table = "product_attribute_value_pos_int"

    value = models.PositiveIntegerField()
    DATATYPE = _ProductAttrValueDataType.POSITIVE_INTEGER


class ProductAttributeValueInt(BaseProductAttributeValue):
    class Meta:
        db_table = "product_attribute_value_int"

    value = models.IntegerField()
    DATATYPE = _ProductAttrValueDataType.INTEGER


class ProductAttributeValueFloat(BaseProductAttributeValue):
    class Meta:
        db_table = "product_attribute_value_float"

    value = models.FloatField()
    DATATYPE = _ProductAttrValueDataType.FLOAT


ProductAttributeValueStr.set_related_name(
    field_name="attr_type", value=_ProductAttrValueDataType.related_field_name.STRING
)
ProductAttributeValueInt.set_related_name(
    field_name="attr_type", value=_ProductAttrValueDataType.related_field_name.INTEGER
)
ProductAttributeValuePosInt.set_related_name(
    field_name="attr_type",
    value=_ProductAttrValueDataType.related_field_name.POSITIVE_INTEGER,
)
ProductAttributeValueFloat.set_related_name(
    field_name="attr_type", value=_ProductAttrValueDataType.related_field_name.FLOAT
)


class ProductAppliedAttributePrice(SoftDeleteObjectMixin):
    """
    describe pricing method, extra amount of money will be charged if customer
    orders a product customized with certain attribute values in the table above
    """

    SOFTDELETE_CHANGESET_MODEL = ProductmgtChangeSet
    SOFTDELETE_RECORD_MODEL = ProductmgtSoftDeleteRecord

    class Meta:
        db_table = "product_applied_attribute_price"

    allowed_models = (
        models.Q(app_label="product", model="ProductAttributeValueStr")
        | models.Q(app_label="product", model="ProductAttributeValueFloat")
        | models.Q(app_label="product", model="ProductAttributeValuePosInt")
        | models.Q(app_label="product", model="ProductAttributeValueInt")
    )
    attrval_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        null=False,
        db_column="attrval_type",
        limit_choices_to=allowed_models,
    )
    attrval_id = models.PositiveIntegerField(db_column="attrval_id")
    # TODO, how to use GenericForeignKey on one-to-one relationship
    # (between attribute value class and  this class)
    attrval_ref = GenericForeignKey(ct_field="attrval_type", fk_field="attrval_id")
    amount = models.FloatField(default=0.00)


class RemoteUserAccountManager(models.Manager):
    def get(self, profile):
        instance = self.model(profile=profile)
        return instance


class RemoteUserAccount(models.Model):
    # read-only model to represent LoginAccount in user_management app
    # Note this app doesn't install Django auth app, so I cannot simply use proxy
    # model on LoginAccount
    class Meta:
        managed = False
        swappable = "AUTH_USER_MODEL"
        db_table = "login_account"

    objects = RemoteUserAccountManager()

    profile = models.PositiveIntegerField(primary_key=True)

    is_superuser = models.BooleanField(
        ("superuser status"),
        default=False,
        help_text=(
            "Designates that this user has all permissions without "
            "explicitly assigning them."
        ),
    )
    is_staff = models.BooleanField(
        ("staff status"),
        default=False,
        help_text=("Designates whether the user can log into this admin site."),
    )

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True


# class ProductPriceHistory(models.Model):
#     class Meta:
#         db_table = 'product_price_history'
#     # the product item at here must be saleable
#     saleable_item  = models.ForeignKey(ProductItem, db_column='saleable_item', on_delete=models.CASCADE,
#                             limit_choices_to=models.Q(category=ProductItemCategory.FINISHED_GOODS))
#     price = models.FloatField(default=0.00)
#     applied_until = models.DateTimeField()
