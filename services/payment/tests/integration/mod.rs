use actix_web::http::header::ContentType;
use actix_web::test::{call_service, init_service, TestRequest};
use serde_json::Value as JsnVal;
use std::fs::File;

use payment::api::web::AppRouteTable;
use payment::network::app_web_service;

#[actix_web::test]
async fn charge_ok() {
    let cfg_routes = [
        ("/charge/{charge_id}", "create_new_charge"),
        ("/charge/{charge_id}", "refresh_charge_status"),
    ]
    .into_iter()
    .map(|(path, inner_label)| (path.to_string(), inner_label.to_string()))
    .collect::<Vec<_>>();
    let route_table = AppRouteTable::default();
    let (app, num_applied) = app_web_service(route_table, cfg_routes);
    assert_eq!(num_applied, 2);
    let mock_app = init_service(app).await;

    const CASE_FILE: &str = "./tests/integration/examples/create_charge_stripe_ok.json";
    let req = {
        let rdr = File::open(CASE_FILE).unwrap();
        let req_body = serde_json::from_reader::<File, JsnVal>(rdr).unwrap();
        TestRequest::post()
            .uri("/v0.0.1/charge/127-203948892-2903")
            .append_header(ContentType::json())
            .set_json(req_body)
            .to_request()
    };
    let resp = call_service(&mock_app, req).await;
    assert_eq!(resp.status().as_u16(), 202);

    let req = {
        TestRequest::patch()
            .uri("/v0.0.1/charge/127-203948892-2903")
            .append_header(ContentType::json())
            .to_request()
    };
    let resp = call_service(&mock_app, req).await;
    assert_eq!(resp.status().as_u16(), 200);
} // end of fn charge_ok
