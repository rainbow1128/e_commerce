use std::result::Result as DefaultResult;

use chrono::DateTime;
use order::api::web::dto::OrderLineReqDto;
use order::constant::ProductType;
use order::error::{AppError, AppErrorCode};
use order::model::{
    ProductPolicyModelSet, ProductPolicyModel, ProductPriceModelSet, ProductPriceModel,
    OrderLineModelSet, OrderLinePriceModel, OrderLineQuantityModel, OrderLineAppliedPolicyModel,
    OrderLineModel
};
use order::repository::AbsOrderRepo;
use order::usecase::{CreateOrderUseCase, CreateOrderUsKsErr, OrderDiscardUnpaidItemsUseCase};

use super::{ut_setup_share_state, MockOrderRepo};

fn ut_setup_prod_policies () -> ProductPolicyModelSet
{
    ProductPolicyModelSet {policies: vec![
        ProductPolicyModel {product_type:ProductType::Package, product_id:168,
            warranty_hours:127, auto_cancel_secs:1008, is_create:false },
        ProductPolicyModel {product_type:ProductType::Item, product_id:168,
            warranty_hours:20000, auto_cancel_secs:1250, is_create:false },
        ProductPolicyModel {product_type:ProductType::Package, product_id:174,
            warranty_hours:30000, auto_cancel_secs:2255, is_create:false },
    ]}
}

fn ut_setup_prod_prices () -> Vec<ProductPriceModelSet>
{
    vec![
        ProductPriceModelSet {store_id:51, items:vec![
            ProductPriceModel {product_type:ProductType::Item, product_id:168,
                start_after:DateTime::parse_from_rfc3339("2023-07-31T10:16:54+05:00").unwrap().into(),
                end_before:DateTime::parse_from_rfc3339("2023-10-10T09:01:31+02:00").unwrap().into(),
                is_create:false, price: 510  },
            ProductPriceModel {product_type:ProductType::Package, product_id:168,
                start_after:DateTime::parse_from_rfc3339("2023-07-31T10:16:54+05:00").unwrap().into(),
                end_before:DateTime::parse_from_rfc3339("2023-10-10T09:01:31+02:00").unwrap().into(),
                is_create:false, price: 1130  },
        ]},
        ProductPriceModelSet {store_id:52, items:vec![
            ProductPriceModel {product_type:ProductType::Item, product_id:168,
                start_after:DateTime::parse_from_rfc3339("2023-07-31T11:29:04+02:00").unwrap().into(),
                end_before:DateTime::parse_from_rfc3339("2023-08-30T09:01:31-08:00").unwrap().into(),
                is_create:false, price: 480  },
            ProductPriceModel {product_type:ProductType::Package, product_id:900,
                start_after:DateTime::parse_from_rfc3339("2023-05-01T21:49:04+02:00").unwrap().into(),
                end_before:DateTime::parse_from_rfc3339("2023-07-31T09:01:55-10:00").unwrap().into(),
                is_create:false, price: 490  },
            ProductPriceModel {product_type:ProductType::Item, product_id:901,
                start_after:DateTime::parse_from_rfc3339("2023-05-01T21:49:04+02:00").unwrap().into(),
                end_before:DateTime::parse_from_rfc3339("2023-07-31T09:01:55-10:00").unwrap().into(),
                is_create:false, price: 399  },
        ]},
    ]
}

#[test]
fn validate_orderline_ok ()
{
    let ms_policy = ut_setup_prod_policies();
    let ms_price = ut_setup_prod_prices();
    let data = vec![
        OrderLineReqDto {seller_id:52, product_type:ProductType::Item,
            product_id:168, quantity:6 },
        OrderLineReqDto {seller_id:51, product_type:ProductType::Package,
            product_id:168, quantity:1 },
        OrderLineReqDto {seller_id:51, product_type:ProductType::Item,
            product_id:168, quantity:10 },
    ];
    let result = CreateOrderUseCase::validate_orderline(ms_policy, ms_price, data);
    assert!(result.is_ok());
    if let Ok(v) = result {
        assert_eq!(v.len(), 3);
        let found = v.iter().any(|m| {
            m.seller_id==52 && m.product_type==ProductType::Item && m.product_id==168
        });
        assert!(found);
        let found = v.iter().any(|m| {
            m.seller_id==51 && m.product_type==ProductType::Item && m.product_id==168
        });
        assert!(found);
        let found = v.iter().any(|m| {
            m.seller_id==51 && m.product_type==ProductType::Package && m.product_id==168
        });
        assert!(found);
    }
} // end of fn validate_orderline_ok

#[test]
fn validate_orderline_missing_properties ()
{
    let ms_policy = ut_setup_prod_policies();
    let ms_price = ut_setup_prod_prices();
    let data = vec![
        OrderLineReqDto {seller_id:52, product_type:ProductType::Package,
            product_id:174, quantity:4 },
        OrderLineReqDto {seller_id:52, product_type:ProductType::Package,
            product_id:900, quantity:2 },
        OrderLineReqDto {seller_id:51, product_type:ProductType::Package,
            product_id:168, quantity:11 },
        OrderLineReqDto {seller_id:52, product_type:ProductType::Item,
            product_id:901, quantity:9 },
    ];
    let result = CreateOrderUseCase::validate_orderline(ms_policy, ms_price, data);
    assert!(result.is_err());
    if let Err(CreateOrderUsKsErr::Client(v)) = result {
        let errs = v.order_lines.unwrap();
        assert_eq!(errs.len(), 3);
        let found = errs.iter().find(|e| {
            e.seller_id==52 && e.product_type==ProductType::Package && e.product_id==900
        }).unwrap();
        if let Some(v) = found.nonexist.as_ref() {
            assert!(v.product_policy);
            assert!(!v.product_price);
        }
        let found = errs.iter().find(|e| {
            e.seller_id==52 && e.product_type==ProductType::Item && e.product_id==901
        }).unwrap();
        if let Some(v) = found.nonexist.as_ref() {
            assert!(v.product_policy);
            assert!(!v.product_price);
        }
        let found = errs.iter().find(|e| {
            e.seller_id==52 && e.product_type==ProductType::Package && e.product_id==174
        }).unwrap();
        if let Some(v) = found.nonexist.as_ref() {
            assert!(!v.product_policy);
            assert!(v.product_price);
        }
    }
} // end of validate_orderline_missing_properties


fn ut_setup_orderlines () -> Vec<OrderLineModel>
{
    let paid_last_update = Some(DateTime::parse_from_rfc3339("2023-11-15T09:23:49+02:00").unwrap());
    let reserved_until = DateTime::parse_from_rfc3339("2023-11-15T09:23:50+02:00").unwrap();
    let warranty_until = DateTime::parse_from_rfc3339("2023-12-24T13:39:41+02:00").unwrap();
    vec![
        OrderLineModel {seller_id:108 , product_type:ProductType::Item,
            product_id: 190, price:OrderLinePriceModel { unit:10, total: 39 },
            qty: OrderLineQuantityModel {reserved: 4, paid: 3, paid_last_update},
            policy: OrderLineAppliedPolicyModel { reserved_until, warranty_until }
        },
        OrderLineModel {seller_id:800, product_type:ProductType::Item,
            product_id: 191, price:OrderLinePriceModel { unit:12, total: 60 },
            qty: OrderLineQuantityModel {reserved: 5, paid: 5, paid_last_update},
            policy: OrderLineAppliedPolicyModel { reserved_until, warranty_until }
        },
        OrderLineModel {seller_id:426, product_type:ProductType::Package,
            product_id: 192, price:OrderLinePriceModel { unit:12, total: 60 },
            qty: OrderLineQuantityModel {reserved: 8, paid: 5, paid_last_update},
            policy: OrderLineAppliedPolicyModel { reserved_until, warranty_until }
        },
    ]
}


async fn discard_unpaid_items_common(
        stock_return_results: Vec<DefaultResult<(), AppError>>,
        fetched_ol_sets:Vec<OrderLineModelSet>,
        oline_cancel_results: Vec<DefaultResult<(), AppError>>
    )
    -> DefaultResult<(), AppError>
{
    let shr_state = ut_setup_share_state();
    let logctx = shr_state.log_context().clone();
    let not_impl_err = AppError{detail:None, code:AppErrorCode::NotImplemented};
    let repo = MockOrderRepo::build(
        Err(not_impl_err.clone()),
        Err(not_impl_err.clone()),
        stock_return_results,
        fetched_ol_sets,
        oline_cancel_results
    );
    let repo:Box<dyn AbsOrderRepo> = Box::new(repo);
    let uc = OrderDiscardUnpaidItemsUseCase::new(repo, logctx);
    uc.execute().await
}

#[tokio::test]
async fn discard_unpaid_items_ok()
{
    let mut mocked_olines = ut_setup_orderlines();
    let stock_return_results = vec![ Ok(()), Ok(()) ];
    let fetched_ol_sets = vec![
        OrderLineModelSet {order_id:"xx1".to_string(), lines:mocked_olines.drain(0..2).collect()},
        OrderLineModelSet {order_id:"xx2".to_string(), lines:mocked_olines},
    ];
    let oline_cancel_results = vec![ Ok(()), Ok(()) ];
    let result = discard_unpaid_items_common(
        stock_return_results, fetched_ol_sets, oline_cancel_results
    ).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn discard_unpaid_items_err_stocklvl()
{
    let mut mocked_olines = ut_setup_orderlines();
    let data_corrupt = AppError{detail:Some(format!("unit-test")), code:AppErrorCode::DataCorruption};
    let stock_return_results = vec![ Ok(()), Err(data_corrupt) ];
    let fetched_ol_sets = vec![
        OrderLineModelSet {order_id:"xx1".to_string(), lines:mocked_olines.drain(0..1).collect()},
        OrderLineModelSet {order_id:"xx2".to_string(), lines:mocked_olines},
    ];
    let oline_cancel_results = vec![ Ok(()), Ok(()) ];
    let result = discard_unpaid_items_common(
        stock_return_results, fetched_ol_sets, oline_cancel_results
    ).await;
    assert!(result.is_err());
    if let Err(e) = result {
        assert_eq!(e.code, AppErrorCode::DataCorruption);
        assert_eq!(e.detail.as_ref().unwrap(), "unit-test");
    }
}

#[tokio::test]
async fn discard_unpaid_items_err_o_repo()
{
    let mut mocked_olines = ut_setup_orderlines();
    let data_corrupt = AppError{detail:Some(format!("unit-test")), code:AppErrorCode::DataCorruption};
    let stock_return_results = vec![ Ok(()), Ok(()) ];
    let fetched_ol_sets = vec![
        OrderLineModelSet {order_id:"xx1".to_string(), lines:mocked_olines.drain(0..1).collect()},
        OrderLineModelSet {order_id:"xx2".to_string(), lines:mocked_olines},
    ];
    let oline_cancel_results = vec![ Ok(()), Err(data_corrupt) ];
    let result = discard_unpaid_items_common(
        stock_return_results, fetched_ol_sets, oline_cancel_results
    ).await;
    assert!(result.is_err());
    if let Err(e) = result {
        assert_eq!(e.code, AppErrorCode::DataCorruption);
        assert_eq!(e.detail.as_ref().unwrap(), "unit-test");
    }
}
