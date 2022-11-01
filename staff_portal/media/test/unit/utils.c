#include <cgreen/cgreen.h>
#include "utils.h"
#include "base64.h"

#define  NUM_TEST_NODES 8
Ensure(app_llnode_link_test) {
    app_llnode_t nodes[NUM_TEST_NODES];
    app_llnode_t *curr, *prev, *new;
    memset(&nodes[0], 0x0, sizeof(nodes));
    {
        new = &nodes[5];
        assert_that(new->next, is_null);
        assert_that(new->prev, is_null);
        app_llnode_link(NULL, NULL, new);
        assert_that(new->next, is_null);
        assert_that(new->prev, is_null);
    }
    { // 7 --> 0
        new  = &nodes[0];
        prev = &nodes[NUM_TEST_NODES - 1];
        app_llnode_link(NULL, prev, new);
        assert_that(new->prev , is_equal_to(prev));
        assert_that(prev->next, is_equal_to(new));
    }
    { // 6 --> 1
        new  = &nodes[6];
        curr = &nodes[1];
        app_llnode_link(curr, NULL, new);
        assert_that(new->next , is_equal_to(curr));
        assert_that(curr->prev, is_equal_to(new));
    }
    { // 7 --> 0 --> 3 --> 6 --> 1
        new  = &nodes[3];
        curr = &nodes[6];
        prev = &nodes[0];
        assert_that(new->next, is_null);
        assert_that(new->prev, is_null);
        app_llnode_link(curr, prev, new);
        assert_that(new->next , is_equal_to(curr));
        assert_that(new->prev , is_equal_to(prev));
        assert_that(curr->prev, is_equal_to(new));
        assert_that(prev->next, is_equal_to(new));
    }
    { // 7 --> 0 --> 3 --> 6 --> 1 --> 4 --> 2 --> 5
        app_llnode_link(&nodes[5], &nodes[4], &nodes[2]);
        app_llnode_link(&nodes[2], &nodes[1], &nodes[4]);
        size_t expect_idx[NUM_TEST_NODES] = {7, 0, 3, 6, 1, 4, 2, 5};
        size_t idx = 0;
        for(curr = &nodes[7]; curr; curr = curr->next) {
            app_llnode_t *expect_node = & nodes[expect_idx[idx++]];
            assert_that(curr, is_equal_to(expect_node));
        }
        for(curr = &nodes[5]; curr; curr = curr->prev) {
            app_llnode_t *expect_node = & nodes[expect_idx[--idx]];
            assert_that(curr, is_equal_to(expect_node));
        }
    }
    { // 7 --> 0 --> 3 --> 6 --> 1 --> 4 --> 2
        prev = &nodes[2];
        curr = &nodes[5];
        assert_that(curr->next , is_null);
        assert_that(curr->prev , is_equal_to(prev));
        app_llnode_unlink(curr);
        assert_that(curr->next , is_null);
        assert_that(curr->prev , is_null);
        assert_that(prev->next , is_null);
    }
    { // 0 --> 3 --> 6 --> 1 --> 4 --> 2
        prev = &nodes[7];
        curr = &nodes[0];
        app_llnode_unlink(prev);
        assert_that(prev->next , is_null);
        assert_that(prev->prev , is_null);
        assert_that(curr->prev , is_null);
    }
    { // 0 --> 3 --> 1 --> 4 --> 2
        curr = &nodes[6];
        app_llnode_unlink(curr);
        assert_that(curr->prev , is_null);
        assert_that(curr->next , is_null);
        assert_that(nodes[3].next , is_equal_to(&nodes[1]));
        assert_that(nodes[1].prev , is_equal_to(&nodes[3]));
    }
} // end of app_llnode_link_test
#undef NUM_TEST_NODES

// internal implementation of hsearch_data seems to preserve 2 extra entries, TODO, figure out why
#define  NUM_ENTRIES_HASHMAP  3
Ensure(app_hashmap_access_test) {
    int err = 0;
    int value = 0;
    struct hsearch_data hmap = {0};
    hcreate_r(NUM_ENTRIES_HASHMAP, &hmap);
    err = app_save_int_to_hashmap(&hmap, "arm64", 0xacce55);
    assert_that(err, is_equal_to(1));
    err = app_save_int_to_hashmap(&hmap, "riscv", 0xa15);
    assert_that(err, is_equal_to(1));
    err = app_save_int_to_hashmap(&hmap, "avr", 0xbeef);
    err = app_save_int_to_hashmap(&hmap, "8080", 0x8080);
    err = app_save_int_to_hashmap(&hmap, "IA64", 0x1a64);
    assert_that(err, is_equal_to(1));
    err = app_save_int_to_hashmap(&hmap, "8052", 0x8052);
    assert_that(err, is_equal_to(0));
#pragma GCC diagnostic ignored "-Wpointer-to-int-cast"
#pragma GCC diagnostic ignored "-Wint-to-pointer-cast"
    value = (int) app_fetch_from_hashmap(&hmap, "avr");
    assert_that(value, is_equal_to(0xbeef));
    value = (int) app_fetch_from_hashmap(&hmap, "arm64");
    assert_that(value, is_equal_to(0xacce55));
    value = (int) app_fetch_from_hashmap(&hmap, "IA64");
    assert_that(value, is_equal_to(0x1a64));
    { // can update the data associated with the same key
        value = (int) app_fetch_from_hashmap(&hmap, "8080");
        assert_that(value, is_equal_to(0x8080));
        err = app_save_int_to_hashmap(&hmap, "8080", 0x17ae);
        assert_that(err, is_equal_to(1));
        value = (int) app_fetch_from_hashmap(&hmap, "8080");
        assert_that(value, is_equal_to(0x17ae));
        err = app_save_int_to_hashmap(&hmap, "8080", 0xd1e5);
        assert_that(err, is_equal_to(1));
        value = (int) app_fetch_from_hashmap(&hmap, "8080");
        assert_that(value, is_equal_to(0xd1e5));
    }
#pragma GCC diagnostic pop
#pragma GCC diagnostic pop
    hdestroy_r(&hmap);
} // end of app_hashmap_access_test
#undef  NUM_ENTRIES_HASHMAP


#define  EXPECT_NUM_ITEMS  5
#define  RAW_STRING_LEN    140
Ensure(app_url_decode_query_param_test) {
    const char *kv[EXPECT_NUM_ITEMS][2] = {
        {"cumin", "clove+garlic"},
        {"sesame","coriander"},
        {"wasabi", NULL},
        {"chilli", "bayan=-omega===zoo"},
        {"dill", "mustard"},
    }; // pairs of query parameters expected to be in raw URI
    char raw_query_param[RAW_STRING_LEN] = {0};
    // should NOT include question mark --> `?`  symbol
    snprintf(&raw_query_param[0], (size_t)RAW_STRING_LEN, "%s=%s&%s=%s&%s&%s=%s&%s=%s&", kv[0][0], kv[0][1],
           kv[1][0], kv[1][1], kv[2][0],  kv[3][0], kv[3][1],  kv[4][0], kv[4][1]);
    json_t *map = json_object();
    int actual_num_items = app_url_decode_query_param(&raw_query_param[0], map);
    assert_that(actual_num_items, is_equal_to(EXPECT_NUM_ITEMS));
    for(size_t idx = 0; idx < EXPECT_NUM_ITEMS; idx++) {
        json_t *obj = json_object_get(map, kv[idx][0]);
        if(json_is_string(obj)) {
            const char *expect_val = kv[idx][1];
            const char *actual_val = json_string_value(obj);
            assert_that(actual_val, is_equal_to_string(expect_val));
        } else if(json_is_boolean(obj)) {
            uint8_t actual_val = (uint8_t) json_boolean_value(obj);
            assert_that(actual_val, is_equal_to((uint8_t)1));
        } else {
            assert_that(0, is_equal_to(1));
        }
    } // end of loop
    json_decref(map);
} // end of app_url_decode_query_param_test
#undef  RAW_STRING_LEN
#undef  EXPECT_NUM_ITEMS


Ensure(app_chararray_to_hexstr_test) {
#define NBYTES_IN  5
#define NBYTES_OUT 10
    int err = 0;
    char dummy[2];
    err = app_chararray_to_hexstr(NULL, 3, NULL, 7);
    assert_that(err, is_equal_to(1));
    err = app_chararray_to_hexstr(&dummy[0], 0, (const char *)&dummy[1], 14);
    assert_that(err, is_equal_to(1));
    { // subcase
        char in[NBYTES_IN] = {0xbe, 0x0e, 0x14, 0x3f, 0x51};
        char expect_hex[NBYTES_OUT + 1] = "be0e143f51\x00";
        char actual_hex[NBYTES_OUT + 1] = {0};
        err = app_chararray_to_hexstr(&actual_hex[0], NBYTES_OUT, &in[0], NBYTES_IN);
        assert_that(err, is_equal_to(0));
        assert_that(actual_hex, is_equal_to_string(expect_hex));
    }
    { // subcase
        char in[NBYTES_IN] = {'a', 'B', 'c', '@', 'J'};
        char expect_hex[NBYTES_OUT + 1] = "614263404a\x00";
        char actual_hex[NBYTES_OUT + 1] = {0};
        err = app_chararray_to_hexstr(&actual_hex[0], NBYTES_OUT, &in[0], NBYTES_IN);
        assert_that(err, is_equal_to(0));
        assert_that(actual_hex, is_equal_to_string(expect_hex));
    }
#undef NBYTES_IN 
#undef NBYTES_OUT
} // end of app_chararray_to_hexstr_test


Ensure(app_base64_check_encoded_test) {
    int ok = 0; size_t len = 16;
    ok = is_base64_encoded((const unsigned char *)"g91oi+w3Qur/pcO=", len);
    assert_that(ok, is_equal_to(1));
    ok = is_base64_encoded((const unsigned char *)"piqyRqhM3hoBigh3", len);
    assert_that(ok, is_equal_to(1));
    ok = is_base64_encoded((const unsigned char *)"hw=Efg-Weu/fkr==", len);
    assert_that(ok, is_equal_to(0));
    ok = is_base64_encoded((const unsigned char *)"8hwEfgWeufker+==", len);
    assert_that(ok, is_equal_to(1));
    ok = is_base64_encoded((const unsigned char *)"hwHefgu/fk@r0SjA", len);
    assert_that(ok, is_equal_to(0));
} // end of app_base64_check_encoded_test

TestSuite *app_utils_tests(void)
{
    TestSuite *suite = create_test_suite();
    add_test(suite, app_llnode_link_test);
    add_test(suite, app_hashmap_access_test);
    add_test(suite, app_url_decode_query_param_test);
    add_test(suite, app_chararray_to_hexstr_test);
    add_test(suite, app_base64_check_encoded_test);
    return suite;
} // end of app_utils_tests

