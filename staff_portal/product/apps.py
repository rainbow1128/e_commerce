from django.apps import AppConfig
from common.util.python import BaseUriLookup, BaseTemplateLookup


class WebAPIurl(BaseUriLookup):
    # URLs of web APIs , accessable to end client users
    _urls = {
        'TagView'           : ['tags', 'tag/<slug:pk>', 'tag/<slug:pk>/ancestors', 'tag/<slug:pk>/descendants'],
        'TaggedSaleableView': 'tagged/<slug:tag_id>',
        'AttributeTypeView' : 'attrtypes',
        'FabricationIngredientView' : ['ingredients', 'ingredient/<slug:pk>',],
        'SaleableItemView'  : ['saleableitems', 'saleableitem/<slug:pk>'],
        'SaleablePackageView': ['saleablepkgs', 'saleablepkg/<slug:pk>'],
    } # end of _urls


class ProductConfig(AppConfig):
    name = 'product'
    app_url   = 'productmgt'
    api_url   = WebAPIurl()

    def ready(self):
        from common.util.python.messaging.monkeypatch import patch_kombu_pool
        patch_kombu_pool()
        from common.models.db import monkeypatch_django_db
        monkeypatch_django_db()

