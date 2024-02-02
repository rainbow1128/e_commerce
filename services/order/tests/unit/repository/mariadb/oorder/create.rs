use std::boxed::Box;
use std::sync::Arc;

use chrono::DateTime;
use order::api::dto::{CountryCode, ShippingMethod};
use order::constant::ProductType;
use order::model::{
    ProductStockModel, StockQuantityModel, StoreStockModel, StockLevelModelSet, 
    OrderLineModelSet
};
use order::repository::{AbsOrderRepo, app_repo_order, AppStockRepoReserveReturn, AbsOrderStockRepo};

use super::super::super::in_mem::oorder::{ut_setup_billing, ut_setup_shipping};
use super::super::super::in_mem::oorder::stock::ut_reserve_init_setup;
use super::super::dstore_ctx_setup;
use super::ut_setup_stock_product;

#[cfg(feature="mariadb")]
pub(super) async fn ut_verify_fetch_all_olines_ok(
    o_repo: &Box<dyn AbsOrderRepo> )
{
    let oid = "800eff40".to_string();
    let result = o_repo.fetch_all_lines(oid).await;
    assert!(result.is_ok());
    let lines = result.unwrap();
    assert_eq!(lines.len(), 4);
    lines.into_iter().map(|o| {
        let (id_, price, qty, policy) = (o.id_, o.price, o.qty, o.policy);
        let combo = (id_.store_id, id_.product_type, id_.product_id);
        let expect = match combo {
            (1013, ProductType::Package, 9004) => (2, 0, 3, 6,  true, DateTime::parse_from_rfc3339("3015-11-29T15:07:30-03:00").unwrap()),
            (1013, ProductType::Item, 9006)    => (3, 0, 4, 12, true, DateTime::parse_from_rfc3339("3014-11-29T15:46:43-03:00").unwrap()),
            (1014, ProductType::Package, 9008) => (29, 0, 20, 580, true, DateTime::parse_from_rfc3339("3015-11-29T15:09:30-03:00").unwrap()),
            (1014, ProductType::Item, 9009)    => (6,  0, 15, 90, true,  DateTime::parse_from_rfc3339("3014-11-29T15:48:43-03:00").unwrap()),
            _others => (0, 0, 0, 0, true, DateTime::parse_from_rfc3339("1989-05-30T23:57:59+00:00").unwrap()),
        };
        let actual = (qty.reserved, qty.paid, price.unit, price.total,
                      qty.paid_last_update.is_none(),  policy.warranty_until
                );
        assert_eq!(actual, expect);
    }).count();
}

fn mock_reserve_usr_cb_0(ms:&mut StockLevelModelSet, req:&OrderLineModelSet)
    -> AppStockRepoReserveReturn
{
    let errors = ms.try_reserve(req);
    assert!(errors.is_empty());
    Ok(())
}

#[cfg(feature="mariadb")]
#[tokio::test]
async fn save_contact_ok()
{
    let mock_warranty  = DateTime::parse_from_rfc3339("3015-11-29T15:02:32.056-03:00").unwrap();
    let ds = dstore_ctx_setup();
    let o_repo = app_repo_order(ds).await.unwrap();
    let (mock_oid, mock_store_id) = ("0e927003716a", 1021);
    ut_setup_stock_product(o_repo.stock(), mock_store_id, ProductType::Item, 9003, 15).await;
    ut_reserve_init_setup(o_repo.stock(), mock_reserve_usr_cb_0, mock_warranty,
        mock_store_id, ProductType::Item, 9003, 3, mock_oid).await;
    let mut billings = ut_setup_billing();
    let mut shippings = ut_setup_shipping(&[mock_store_id, 12]);
    let billing = billings.remove(1);
    let shipping = shippings.remove(2);
    let result = o_repo.save_contact(mock_oid, billing, shipping).await;
    assert!(result.is_ok());
    let result = o_repo.fetch_billing(mock_oid.to_string()).await;
    assert!(result.is_ok());
    if let Ok(bl) = result {
        assert_eq!(bl.contact.first_name.as_str(), "Jordan");
        assert_eq!(bl.contact.last_name.as_str(), "NormanKabboa");
        assert_eq!(bl.contact.emails[0].as_str(), "banker@blueocean.ic");
        assert_eq!(bl.contact.emails[1].as_str(), "bee@gituye.com");
        assert_eq!(bl.contact.phones[0].nation, 48u16);
        assert_eq!(bl.contact.phones[0].number.as_str(), "000208126");
        assert_eq!(bl.contact.phones[1].nation, 49u16);
        assert_eq!(bl.contact.phones[1].number.as_str(), "030001211");
        let addr = bl.address.unwrap();
        assert!(matches!(addr.country, CountryCode::US));
        assert_eq!(addr.city.as_str(), "i9ru24t");
        assert_eq!(addr.street_name.as_ref().unwrap().as_str(), "du iye j0y");
        assert_eq!(addr.detail.as_str(), "eu ur4 to4o");
    }
    let result = o_repo.fetch_shipping(mock_oid.to_string()).await;
    assert!(result.is_ok());
    if let Ok(sh) = result {
        assert_eq!(sh.contact.first_name.as_str(), "Biseakral");
        assert_eq!(sh.contact.last_name.as_str(), "Kazzhitsch");
        assert_eq!(sh.contact.emails[0].as_str(), "low@hunt.io");
        assert_eq!(sh.contact.emails[1].as_str(), "axl@rose.com");
        assert_eq!(sh.contact.emails[2].as_str(), "steven@chou01.hk");
        assert_eq!(sh.contact.phones[0].nation, 43u16);
        assert_eq!(sh.contact.phones[0].number.as_str(), "500020812");
        assert!(sh.address.is_none());
        assert_eq!(sh.option[0].seller_id, mock_store_id);
        assert!(matches!(sh.option[0].method, ShippingMethod::FedEx));
    }
} // end of fn save_contact_ok

#[cfg(feature="mariadb")]
#[tokio::test]
async fn save_contact_error()
{
    let mock_warranty  = DateTime::parse_from_rfc3339("3015-11-29T15:02:32.056-03:00").unwrap();
    let ds = dstore_ctx_setup();
    let o_repo = app_repo_order(ds).await.unwrap();
    let (mock_oid, mock_store_id) = ("a4190e9b4272", 1022);
    ut_setup_stock_product(o_repo.stock(), mock_store_id, ProductType::Item, 9003, 15).await;
    ut_reserve_init_setup(o_repo.stock(), mock_reserve_usr_cb_0, mock_warranty,
        mock_store_id, ProductType::Item, 9003, 4, mock_oid).await;
    let mut billings = ut_setup_billing();
    let mut shippings = ut_setup_shipping(&[mock_store_id, 12]);
    let billing = billings.remove(2);
    let shipping = shippings.remove(0);
    let result = o_repo.save_contact(mock_oid, billing, shipping).await;
    assert!(result.is_err()); // no shipping option provided
}

