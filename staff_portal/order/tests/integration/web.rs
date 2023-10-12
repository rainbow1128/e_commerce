use std::result::Result as DefaultResult ;

use hyper::Body as HyperBody;
use http::{Request, StatusCode};

use order::AppRpcClientReqProperty;
use order::error::AppError;
use order::api::web::dto::{
    OrderCreateReqData, OrderCreateRespOkDto, OrderEditReqData, ProductPolicyDto,
    OrderCreateRespErrorDto, ContactErrorReason, PhoneNumNationErrorReason
};
use order::api::rpc;

mod common;
use common::{test_setup_shr_state, TestWebServer, deserialize_json_template};

const FPATH_NEW_ORDER_OK_1:&'static str  = "/tests/integration/examples/order_new_ok_1.json";
const FPATH_NEW_ORDER_CONTACT_ERR:&'static str  = "/tests/integration/examples/order_new_contact_error.json";
const FPATH_EDIT_ORDER_OK_1:&'static str = "/tests/integration/examples/order_edit_ok_1.json";
const FPATH_EDIT_PRODUCTPOLICY_OK_1:&'static str = "/tests/integration/examples/policy_product_edit_ok_1.json";
const FPATH_EDIT_PRODUCTPOLICY_OK_2:&'static str = "/tests/integration/examples/policy_product_edit_ok_2.json";
const FPATH_EDIT_PRODUCTPOLICY_ERR:&'static str = "/tests/integration/examples/policy_product_edit_exceed_limit.json";

#[tokio::test]
async fn place_new_order_ok() -> DefaultResult<(), AppError>
{
    let shr_state = test_setup_shr_state() ? ;
    let srv = TestWebServer::setup(shr_state.clone());
    let top_lvl_cfg = shr_state.config();
    let listener = &top_lvl_cfg.api_server.listen;
    { // ---- add product policy first ----
        let uri = format!("/{}/policy/products", top_lvl_cfg.api_server.listen.api_version);
        let reqbody = {
            let  req_body_template = deserialize_json_template::<Vec<ProductPolicyDto>>
                (&top_lvl_cfg.basepath, FPATH_EDIT_PRODUCTPOLICY_OK_2) ? ;
            assert!(req_body_template.len() > 0);
            let rb = serde_json::to_string(&req_body_template).unwrap();
            HyperBody::from(rb)
        };
        let req = Request::builder().uri(uri.clone()).method("POST")
            .header("content-type", "application/json") .body(reqbody) .unwrap();
        let response = TestWebServer::consume(&srv, req).await;
        assert_eq!(response.status(), StatusCode::OK);
    }
    { // ------- add product price then --------
        let msgbody = br#"
                 [
                     [],
                     {"s_id": 18830, "rm_all": false, "deleting": {"item_type":1, "pkg_type":2},
                      "updating": [],
                      "creating": [
                          {"price": 126, "start_after": "2023-09-04T09:11:13+08:00", "product_type": 1,
                           "end_before": "2023-12-24T07:11:13.730050+08:00", "product_id": 270118},
                          {"price": 135, "start_after": "2023-09-10T09:11:13+09:00", "product_type": 1,
                           "end_before": "2023-12-24T07:11:13.730050+09:00", "product_id": 270119},
                          {"price": 1038, "start_after": "2022-01-20T04:30:58.070020+10:00", "product_type": 2,
                           "end_before": "2024-02-28T18:11:56.877000+10:00", "product_id": 270118}
                      ]
                     },
                     {"callbacks": null, "errbacks": null, "chain": null, "chord": null}
                ]
                "#;
        let req = AppRpcClientReqProperty { retry: 1,  msgbody:msgbody.to_vec(),
                route: "update_store_products".to_string()  };
        let result = rpc::route_to_handler(req, shr_state.clone()).await;
        assert!(result.is_ok());
    }
    { // ------- call create-order web API -----------
        let reqbody = {
            let rb = deserialize_json_template::<OrderCreateReqData>
                (&top_lvl_cfg.basepath, FPATH_NEW_ORDER_OK_1) ? ;
            let rb = serde_json::to_string(&rb) .unwrap();
            HyperBody::from(rb)
        };
        let uri = format!("/{}/order", listener.api_version);
        let req = Request::builder().uri(uri).method("POST")
            .header("content-type", "application/json")
            .header("accept", "application/json")
            .body(reqbody)
            .unwrap();

        let mut response = TestWebServer::consume(&srv, req).await;
        assert_eq!(response.status(), StatusCode::CREATED);
        let actual = TestWebServer::to_custom_type::<OrderCreateRespOkDto>
            (response.body_mut())  .await  ? ;
        assert_eq!(actual.order_id.is_empty() ,  false);
        assert!(actual.reserved_lines.len() > 0);
    }
    Ok(())
} // end of place_new_order_ok


#[tokio::test]
async fn place_new_order_contact_error() -> DefaultResult<(), AppError>
{
    let shr_state = test_setup_shr_state() ? ;
    let srv = TestWebServer::setup(shr_state.clone());
    let top_lvl_cfg = shr_state.config();
    let listener = &top_lvl_cfg.api_server.listen;
    let reqbody = {
        let rb = deserialize_json_template::<OrderCreateReqData>
            (&top_lvl_cfg.basepath, FPATH_NEW_ORDER_CONTACT_ERR) ? ;
        let rb = serde_json::to_string(&rb) .unwrap();
        HyperBody::from(rb)
    };
    let uri = format!("/{}/order", listener.api_version);
    let req = Request::builder().uri(uri).method("POST")
        .header("content-type", "application/json")
        .header("accept", "application/json")
        .body(reqbody)  .unwrap();

    let mut response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    let actual = TestWebServer::to_custom_type::<OrderCreateRespErrorDto>
        (response.body_mut())  .await  ? ;
    let contact_err = actual.shipping.unwrap().contact.unwrap();
    let (name_err, phone_err) = (contact_err.first_name.unwrap(),
                                 contact_err.phones.unwrap());
    assert!(matches!(name_err, ContactErrorReason::Empty));
    assert_eq!(phone_err.len(), 2);
    assert!(phone_err[0].is_none());
    let ph_err_1 = phone_err[1].as_ref().unwrap();
    assert!(matches!(ph_err_1.nation.as_ref().unwrap(), PhoneNumNationErrorReason::InvalidCode));
    Ok(())
} // end of place_new_order_contact_error


#[tokio::test]
async fn edit_order_contact_ok() -> DefaultResult<(), AppError>
{
    let shr_state = test_setup_shr_state() ? ;
    let srv = TestWebServer::setup(shr_state.clone());
    let top_lvl_cfg = shr_state.config();
    let reqbody = {
        let mut rb = deserialize_json_template::<OrderEditReqData>
            (&top_lvl_cfg.basepath, FPATH_EDIT_ORDER_OK_1) ? ;
        use std::fmt::Write;
        rb.billing.contact.first_name.clear();
        rb.billing.contact.first_name.write_str("Satunam") .unwrap();
        let rb = serde_json::to_string(&rb).unwrap();
        HyperBody::from(rb)
    };
    let uri = format!("/{ver}/order/{oid}", oid = "r8dj30H",
                      ver = top_lvl_cfg.api_server.listen.api_version);
    let req = Request::builder().uri(uri).method("PATCH")
        .header("content-type", "application/json")
        .body(reqbody)
        .unwrap();

    let response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::OK);
    Ok(())
}

#[tokio::test]
async fn add_product_policy_ok() -> DefaultResult<(), AppError>
{
    let shr_state = test_setup_shr_state() ? ;
    let srv = TestWebServer::setup(shr_state.clone());
    let top_lvl_cfg = shr_state.config();
    let uri = format!("/{}/policy/products", top_lvl_cfg.api_server.listen.api_version);
    let mut req_body_template = deserialize_json_template::<Vec<ProductPolicyDto>>
            (&top_lvl_cfg.basepath, FPATH_EDIT_PRODUCTPOLICY_OK_1) ? ;
    assert!(req_body_template.len() > 0);
    // ---- subcase 1 ----
    let reqbody = {
        let item = req_body_template.get_mut(0).unwrap();
        item.warranty_hours = 2345;
        let rb = serde_json::to_string(&req_body_template).unwrap();
        HyperBody::from(rb)
    };
    let req = Request::builder().uri(uri.clone()).method("POST")
        .header("content-type", "application/json") .body(reqbody) .unwrap();
    let response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::OK);
    // ---- subcase 2 ----
    let reqbody = {
        let item = req_body_template.get_mut(0).unwrap();
        item.auto_cancel_secs = 309;
        let item = req_body_template.get_mut(1).unwrap();
        item.product_id = 7788;
        let rb = serde_json::to_string(&req_body_template).unwrap();
        HyperBody::from(rb)
    };
    let req = Request::builder().uri(uri.clone()).method("POST")
        .header("content-type", "application/json") .body(reqbody) .unwrap();
    let response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::OK);
    Ok(())
} // end of fn add_product_policy_ok

#[tokio::test]
async fn add_product_policy_error() -> DefaultResult<(), AppError>
{
    let shr_state = test_setup_shr_state() ? ;
    let srv = TestWebServer::setup(shr_state.clone());
    let top_lvl_cfg = shr_state.config();
    let uri = format!("/{}/policy/products", top_lvl_cfg.api_server.listen.api_version);
    // ---- subcase 1 ----
    let reqbody = HyperBody::from("[]".to_string());
    let req = Request::builder().uri(uri.clone()).method("POST")
        .header("content-type", "application/json") .body(reqbody) .unwrap();
    let response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    // ---- subcase 2 ----
    let reqbody = {
        let rb = deserialize_json_template::<Vec<ProductPolicyDto>>
            (&top_lvl_cfg.basepath, FPATH_EDIT_PRODUCTPOLICY_ERR) ? ;
        let rb = serde_json::to_string(&rb).unwrap();
        HyperBody::from(rb)
    };
    let req = Request::builder().uri(uri).method("POST")
        .header("content-type", "application/json") .body(reqbody) .unwrap();
    let mut response = TestWebServer::consume(&srv, req).await;
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    {
        use http_body::Body as RawHttpBody;
        // required by UnsyncBoxBody, to access raw data of body
        let bd = response.body_mut();
        let result = bd.data().await;
        let rawbytes = result.unwrap().unwrap();
        println!("response body content, first 50 bytes : {:?}", rawbytes.slice(..50) );
    }
    Ok(())
} // end of fn add_product_policy_error

