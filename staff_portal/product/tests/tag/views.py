import random

from functools import partial
from unittest.mock import Mock, patch

from django.test import TransactionTestCase
from django.contrib.auth.models import User as AuthUser
from rest_framework.settings import DEFAULTS as drf_default_settings

from product.permissions import TagsPermissions
from product.tests.common import _fixtures, _MockTestClientInfoMixin, assert_view_bulk_create_with_response, assert_view_permission_denied
from .common import TreeNodeMixin, HttpRequestDataGenTag, TagVerificationMixin

class TagBaseViewTestCase(TransactionTestCase, _MockTestClientInfoMixin,  HttpRequestDataGenTag, TagVerificationMixin):
    permission_class = TagsPermissions

    def setUp(self):
        _user_info = _fixtures['AuthUser'][0]
        account = AuthUser(**_user_info)
        account.set_password(_user_info['password'])
        account.save()
        # for django app, header name has to start with `HTTP_XXXX`
        self.http_forwarded = self._forwarded_pattern % _user_info['username']

    def tearDown(self):
        self._client.cookies.clear()

    def _send_request_to_backend(self, path, method='post', body=None, expect_shown_fields=None,
            ids=None, extra_query_params=None):
        headers = {'HTTP_FORWARDED': self.http_forwarded,}
        return super()._send_request_to_backend( path=path, method=method, body=body, ids=ids,
                expect_shown_fields=expect_shown_fields, extra_query_params=extra_query_params,
                headers=headers)
## end of class TagBaseViewTestCase


class TagCreationTestCase(TagBaseViewTestCase):
    path = '/tags'

    def setUp(self):
        super().setUp()
        self.num_trees = 2
        self._origin_trees, self._request_data = self.refresh_req_data( shuffle=True, num_trees=self.num_trees,
                min_num_nodes=15, max_num_nodes=25, min_num_siblings=2, max_num_siblings=3)

    def test_permission_denied(self):
        kwargs = {
            'testcase':self, 'request_body_data':'', 'path':self.path, 'content_type':self._json_mimetype,
            'mock_rpc_path': 'product.views.base.TagView._usermgt_rpc.get_profile',
            'http_forwarded':self.http_forwarded, 'permission_map':self.permission_class.perms_map['POST'],
            'return_profile_id':self.mock_profile_id[0], 'http_method':'post'
        }
        assert_view_permission_denied(**kwargs)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_new_trees(self, mock_get_profile):
        expect_shown_fields = ['id', 'name',]
        expect_hidden_fields = ['ancestors', 'descendants']
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'POST')
        response = assert_view_bulk_create_with_response(testcase=self, expect_shown_fields=expect_shown_fields,
                expect_hidden_fields=expect_hidden_fields, path=self.path, body=self._request_data,
                method='post')
        created_tags = response.json()
        tag_ids = list(map(lambda d: d['id'], created_tags))
        entity_data, closure_data = self.load_closure_data(node_ids=tag_ids)
        saved_trees = TreeNodeMixin.gen_from_closure_data(entity_data=entity_data, closure_data=closure_data)
        matched, not_matched = TreeNodeMixin.compare_trees(trees_a=self._origin_trees, trees_b=saved_trees,
                value_compare_fn=self._value_compare_fn)
        self.assertListEqual(not_matched, [])
        self.assertEqual(len(matched), len(self._origin_trees))
        # ---- append new trees to existing nodes ----
        curr_node = saved_trees[0]
        while any(curr_node.children):
            sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
            curr_node = sorted_children[-1]
        tree, req_data = self.refresh_req_data( shuffle=True, num_trees=1,
                min_num_nodes=7, max_num_nodes=15, min_num_siblings=2, max_num_siblings=2)
        tree[0].parent = curr_node
        tree_root_req_data = list(filter(lambda d:d['new_parent'] is None, req_data))
        tree_root_req_data = tree_root_req_data[0]
        tree_root_req_data['exist_parent'] = tree[0].parent.value['id']
        tree, req_data_2 = self.refresh_req_data( shuffle=True, num_trees=1,
                min_num_nodes=7, max_num_nodes=15, min_num_siblings=2, max_num_siblings=2)
        def _adjust_new_parent_pos(d):
            if d['new_parent'] is not None:
                d['new_parent'] += len(req_data)
            return d
        tuple(map(_adjust_new_parent_pos, req_data_2))
        req_data.extend(req_data_2)
        saved_trees.append(tree[0])
        response = assert_view_bulk_create_with_response(testcase=self, expect_shown_fields=expect_shown_fields,
                expect_hidden_fields=expect_hidden_fields, path=self.path, body=req_data,  method='post')
        created_tags = response.json()
        tag_ids.extend( list(map(lambda d: d['id'], created_tags)) )
        entity_data, closure_data = self.load_closure_data(node_ids=tag_ids)
        saved_trees_2 = TreeNodeMixin.gen_from_closure_data(entity_data=entity_data, closure_data=closure_data)
        matched, not_matched = TreeNodeMixin.compare_trees(trees_a=saved_trees, trees_b=saved_trees_2,
                value_compare_fn=self._value_compare_fn)
        self.assertListEqual(not_matched, [])
        self.assertEqual(len(matched), len(saved_trees))


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_loop_detection(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'POST')
        num_nodes = 4
        tree_nodes = [TreeNodeMixin(value={'name': 'tag %s' % (idx),}) for idx in range(num_nodes)]
        for idx in range(num_nodes - 1):
            tree_nodes[idx+1].parent = tree_nodes[idx]
        trees = [tree_nodes[0]]
        req_data = self.trees_to_req_data(trees=trees)
        tree_nodes[0].parent =  tree_nodes[-1]
        req_data[0]['new_parent'] = num_nodes - 1
        response = self._send_request_to_backend(path=self.path, body=req_data,  method='post',
                expect_shown_fields=['id', 'name',])
        self.assertEqual(int(response.status_code), 400)
        err_info = response.json()
        non_field_err_key = drf_default_settings['NON_FIELD_ERRORS_KEY']
        err_info = err_info[non_field_err_key]
        loop_detect_msg_pos = err_info[0].find(self.err_msg_loop_detected)
        self.assertGreater(loop_detect_msg_pos, 0)
## end of class TagCreationTestCase


class TagUpdateBaseTestCase(TagBaseViewTestCase):
    num_trees = 3
    min_num_nodes = 15
    max_num_nodes = 25
    min_num_siblings = 2
    max_num_siblings = 3

    def setUp(self):
        super().setUp()
        path = '/tags'
        trees, request_data = self.refresh_req_data( shuffle=True, num_trees=self.num_trees,
                min_num_nodes=self.min_num_nodes, max_num_nodes=self.max_num_nodes,
                min_num_siblings=self.min_num_siblings, max_num_siblings=self.max_num_siblings )
        with patch('product.views.base.TagView._usermgt_rpc.get_profile') as mock_get_profile:
            expect_usrprof = self.mock_profile_id[0]
            mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'POST')
            response = self._send_request_to_backend(path=path, body=request_data,
                    method='post', expect_shown_fields=['id', 'name',])
            self.assertEqual(int(response.status_code), 201)
            created_items = response.json()
            tag_ids = tuple(map(lambda x:x['id'], created_items))
            entity_data, closure_data = self.load_closure_data(node_ids=tag_ids)
            self._origin_trees = TreeNodeMixin.gen_from_closure_data(entity_data=entity_data, closure_data=closure_data)



class TagUpdateTestCase(TagUpdateBaseTestCase):
    path = '/tags'

    def test_permission_denied(self):
        kwargs = {
            'testcase':self, 'request_body_data':'', 'path':self.path, 'content_type':self._json_mimetype,
            'mock_rpc_path': 'product.views.base.TagView._usermgt_rpc.get_profile',
            'http_forwarded':self.http_forwarded, 'permission_map':self.permission_class.perms_map['PUT'],
            'return_profile_id':self.mock_profile_id[0], 'http_method':'put'
        }
        assert_view_permission_denied(**kwargs)


    def _update_and_validate(self, moving_nodes, expect_response_status, post_resp_fn=None):
        req_data = list(map(lambda node: {'id':node.value['id'], 'name':node.value['name'], \
                    'exist_parent': node.parent.value['id'] if node.parent else None, \
                    'new_parent':None}, moving_nodes))
        response = self._send_request_to_backend(path=self.path, method='put', body=req_data,
                expect_shown_fields=['id','name'])
        self.assertEqual(int(response.status_code), expect_response_status)
        if post_resp_fn and callable(post_resp_fn):
            post_resp_fn(response=response)

    def _post_update_response_ok(self, response):
        edited_data = response.json()
        self.assertListEqual(edited_data, [])
        saved_trees = TreeNodeMixin.gen_from_closure_data(
                entity_data=self._origin_trees.entity_data,
                closure_data=self._origin_trees.closure_data
            )
        def _value_compare_fn(val_a, val_b):
            return val_a['name'] == val_b['name'] and val_a['id'] == val_b['id']
        matched, not_matched = TreeNodeMixin.compare_trees(trees_a=saved_trees,
                trees_b=self._origin_trees, value_compare_fn=_value_compare_fn)
        self.assertListEqual(not_matched, [])
        self.assertEqual(len(matched), len(saved_trees))


    def _post_update_response_loop_detected(self, response,  expect_loop_nodes):
        err_info  = response.json()
        non_field_err_key = drf_default_settings['NON_FIELD_ERRORS_KEY']
        err_info = err_info[non_field_err_key]
        pattern_pos = err_info[0].find(self.err_msg_loop_detected)
        self.assertGreater(pattern_pos, 0)
        for loop_node in expect_loop_nodes:
            form_label_pattern = 'form #%s'
            pattern_pos = err_info[0].find(form_label_pattern % loop_node.value['id'])
            self.assertGreaterEqual(pattern_pos, 0)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_subtrees_to_new_root(self , mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'PUT')
        extracted_subtrees = []
        moving_nodes = []
        roots = self._origin_trees
        #-------------------------------
        for root in roots:
            curr_node = root
            while any(curr_node.children):
                sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
                curr_node = sorted_children[-1]
            extracted_subtrees.append(curr_node.parent)
        #-------------------------------
        for subtree in extracted_subtrees[1:] :
            curr_node = extracted_subtrees[0]
            while any(curr_node.children):
                rand_idx = random.randrange(0, len(curr_node.children))
                curr_node = curr_node.children[rand_idx]
            parent_to = curr_node
            moving_node = subtree
            moving_node.parent = parent_to
            moving_nodes.append(moving_node)
        extracted_subtrees[0].parent = None
        moving_nodes.append(extracted_subtrees[0])
        self._origin_trees.append(extracted_subtrees[0])
        self._update_and_validate(moving_nodes, expect_response_status=200,
                post_resp_fn=self._post_update_response_ok)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_tree_chains(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'PUT')
        moving_nodes = []
        moving_node  = None
        roots = self._origin_trees
        curr_node = roots[0]
        while any(curr_node.children):
            curr_node = curr_node.children[-1]
        parent_to = curr_node
        while moving_node is not roots[1]:
            # gradually extract subtrees of roots[1] and append it to roots[0]
            curr_node = roots[1]
            while any(curr_node.children):
                sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
                curr_node = sorted_children[-1]
            moving_node = curr_node.parent
            moving_node.parent = parent_to
            moving_nodes.append(moving_node)
            parent_to = moving_node.children[0]
        #-------------------------------
        self._origin_trees.remove(roots[1])
        self._update_and_validate(moving_nodes, expect_response_status=200,
                post_resp_fn=self._post_update_response_ok)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_loop_detection(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'PUT')
        moving_nodes = []
        moving_node  = None
        chosen_subtrees = []
        roots = self._origin_trees
        for root in roots:
            curr_node = root
            while any(curr_node.children):
                sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
                curr_node = sorted_children[-1]
            chosen_subtrees.append(curr_node.parent)
            moving_nodes.append(curr_node.parent)
        expect_loop_nodes = [ chosen_subtrees[2], chosen_subtrees[1], chosen_subtrees[0],
                chosen_subtrees[2].children[0], chosen_subtrees[1].children[0],
                chosen_subtrees[0].children[0]
            ]
        chosen_subtrees[0].parent, chosen_subtrees[1].parent, chosen_subtrees[2].parent = \
                chosen_subtrees[1].children[0], chosen_subtrees[2].children[0], chosen_subtrees[0].children[0]
        bound_cb = partial(self._post_update_response_loop_detected, expect_loop_nodes=expect_loop_nodes)
        self._update_and_validate(moving_nodes, expect_response_status=400, post_resp_fn=bound_cb)
## end of class TagUpdateTestCase


class TagDeletionTestCase(TagUpdateBaseTestCase):
    path = '/tags'

    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_descs_delete(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'DELETE')
        chosen_subtrees = []
        model_cls = self.serializer_class.Meta.model
        for root in self._origin_trees:
            curr_node = root
            while any(curr_node.children):
                sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
                curr_node = sorted_children[-1]
            chosen_subtrees.append(curr_node.parent)
        chosen_tag_ids = tuple(map(lambda t: t.value['id'], chosen_subtrees))
        expect_deleted_tag_ids = model_cls.objects.filter(
                ancestors__ancestor__in=chosen_tag_ids ).values_list(
                'descendants__descendant', flat=True)
        req_data = list(map(lambda n: {'id': n}, chosen_tag_ids))
        response = self._send_request_to_backend(path=self.path, method='delete', body=req_data)
        self.assertEqual(int(response.status_code), 204)
        deleted_tags_exists = model_cls.objects.filter(id__in=expect_deleted_tag_ids).exists()
        self.assertFalse(deleted_tags_exists)
## end of class TagDeletionTestCase


class TagQueryTestCase(TagUpdateBaseTestCase):
    min_num_nodes = 25
    max_num_nodes = 35
    max_num_siblings = 2
    path = ['/tags', '/tag/%s', '/tag/%s/ancestors', '/tag/%s/descendants']

    def _diff(self, expect_objs, actual_objs):
        self.assertEqual(len(expect_objs), len(actual_objs))
        expect_objs = sorted(expect_objs, key=lambda t: t.value['id'])
        actual_objs = sorted(actual_objs, key=lambda d: d['id'])
        actual_objs_iter = iter(actual_objs)
        for expect_obj in expect_objs:
            actual_obj = next(actual_objs_iter)
            self.assertEqual(expect_obj.value['id'],   actual_obj['id'])
            self.assertEqual(expect_obj.value['name'], actual_obj['name'])
            if actual_obj.get('ancestors'):
                expect_parent  = expect_obj
                actual_parents = sorted(actual_obj['ancestors'], key=lambda d:d['depth'])
                for actual_parent in actual_parents:
                    expect_parent = expect_parent.parent
                    self.assertEqual(expect_parent.value['id'],  actual_parent['ancestor'])
            expect_children = tuple(map(lambda t:t.value['id'], expect_obj.children))
            if actual_obj.get('descendants'):
                actual_children = filter(lambda d: d['depth'] == 1, actual_obj['descendants'])
                actual_children = tuple(map(lambda d: d['descendant'], actual_children))
                self.assertSetEqual(set(expect_children), set(actual_children))
            if actual_obj.get('num_children'):
                self.assertEqual(len(expect_children), actual_obj['num_children'])


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_load_specific_many(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'GET')
        chosen_subtrees = []
        for root in self._origin_trees:
            curr_node = root
            while any(curr_node.children):
                sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
                curr_node = sorted_children[-1]
            chosen_subtrees.append(curr_node.parent)
        chosen_tag_ids = tuple(map(lambda t: t.value['id'], chosen_subtrees))
        response = self._send_request_to_backend(path=self.path[0], method='get', ids=chosen_tag_ids)
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=chosen_subtrees, actual_objs=loaded_tags)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_load_specific_one(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'GET')
        chosen_subtree = self._origin_trees[0].children[0]
        path = self.path[1] % chosen_subtree.value['id']
        response = self._send_request_to_backend(path=path, method='get')
        self.assertEqual(int(response.status_code), 200)
        loaded_tag = response.json()
        self._diff(expect_objs=[chosen_subtree], actual_objs=[loaded_tag])


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_load_roots(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'GET')
        origin_trees = self._origin_trees.copy()
        path = self.path[3] % 'root'
        response = self._send_request_to_backend(path=path, method='get',
                expect_shown_fields=['id','name','num_children'])
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=origin_trees, actual_objs=loaded_tags)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_load_descendants(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'GET')
        chosen_subtree = self._origin_trees[0].children[0]
        path = self.path[3] % chosen_subtree.value['id']
        response = self._send_request_to_backend(path=path, method='get',
                expect_shown_fields=['id','name','num_children'])
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=chosen_subtree.children, actual_objs=loaded_tags)


    @patch('product.views.base.TagView._usermgt_rpc.get_profile')
    def test_load_ancestors(self, mock_get_profile):
        expect_usrprof = self.mock_profile_id[0]
        mock_get_profile.return_value = self._mock_get_profile(expect_usrprof, 'GET')
        chosen_parents = []
        curr_node = self._origin_trees[0]
        while any(curr_node.children):
            chosen_parents.append(curr_node)
            sorted_children = sorted(curr_node.children, key=lambda node:node.depth)
            curr_node = sorted_children[-1]
        chosen_subtree = curr_node.parent
        chosen_parents.pop()
        path = self.path[2] % chosen_subtree.value['id']
        #---------------------------------
        response = self._send_request_to_backend(path=path, method='get',
                expect_shown_fields=['id','name','num_children'])
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=chosen_parents[-1:], actual_objs=loaded_tags)
        #---------------------------------
        response = self._send_request_to_backend(path=path, method='get',
                expect_shown_fields=['id','name','num_children'],
                extra_query_params={'depth':2} )
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=chosen_parents[-2:], actual_objs=loaded_tags)
        #---------------------------------
        response = self._send_request_to_backend(path=path, method='get',
                expect_shown_fields=['id','name','num_children'],
                extra_query_params={'depth':-1} ) # load all ancestor nodes
        self.assertEqual(int(response.status_code), 200)
        loaded_tags = response.json()
        self._diff(expect_objs=chosen_parents, actual_objs=loaded_tags)



