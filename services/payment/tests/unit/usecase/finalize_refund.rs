use std::collections::HashMap;
use std::str::FromStr;
use std::sync::Arc;

use chrono::{DateTime, Duration, Local, Utc};
use ecommerce_common::error::AppErrorCode;
use payment::api::web::dto::{RefundCompletionOlineRespDto, RefundRejectReasonDto};
use rust_decimal::Decimal;

use ecommerce_common::api::dto::{CurrencyDto, PayAmountDto};
use ecommerce_common::api::rpc::dto::OrderLineReplicaRefundDto;
use ecommerce_common::constant::ProductType;
use payment::adapter::processor::{AbstractPaymentProcessor, AppProcessorErrorReason};
use payment::adapter::repository::{
    AbstractChargeRepo, AbstractMerchantRepo, AbstractRefundRepo, AppRepoError, AppRepoErrorDetail,
    AppRepoErrorFnLabel,
};
use payment::model::{
    BuyerPayInState, Charge3partyModel, ChargeBuyerModel, MerchantProfileModel,
    OrderCurrencySnapshot, OrderRefundModel, RefundModelError, StripeCheckoutPaymentStatusModel,
};
use payment::usecase::{FinalizeRefundUcError, FinalizeRefundUseCase};

use super::{MockChargeRepo, MockMerchantRepo, MockPaymentProcessor, MockRefundRepo};
use crate::dto::ut_setup_storeprofile_dto;
use crate::model::refund::ut_setup_refund_cmplt_dto;
use crate::model::{
    ut_default_charge_method_stripe, ut_setup_buyer_charge, UTestChargeLineRawData,
};

#[rustfmt::skip]
fn ut_setup_repo_charge(
    charges_by_merchant: Option<Vec<ChargeBuyerModel>>,
    update_line_rfd_res: Option<Result<(), AppRepoError>>,
) -> Box<dyn AbstractChargeRepo > {
    let read_charge_ids = charges_by_merchant.as_ref()
        .map(|d| {
            let buyer_usr_id = d.first().unwrap().meta.owner();
            let ctimes = d.iter().map(|v| v.meta.create_time().clone()).collect();
            (buyer_usr_id, ctimes)
        });
    MockChargeRepo::build(
        None, None, None, None,
        None, None, charges_by_merchant,
        None, None,
        read_charge_ids, update_line_rfd_res,
    )
}

#[rustfmt::skip]
fn ut_setup_repo_merchant(
    saved_prof: Option<MerchantProfileModel>
) -> Box<dyn AbstractMerchantRepo> {
    MockMerchantRepo::build(None, None, saved_prof, None)
}

fn ut_setup_repo_refund(saved_req: Option<OrderRefundModel>) -> Box<dyn AbstractRefundRepo> {
    MockRefundRepo::build(saved_req)
}

fn ut_setup_processor(trigs: Option<Vec<bool>>) -> Arc<Box<dyn AbstractPaymentProcessor>> {
    let obj = MockPaymentProcessor::build(None, None, None, None, trigs);
    Arc::new(obj)
}

#[rustfmt::skip]
fn ut_setup_buyer_charge_inner(
    mock_oid: &str, charge_ctime: DateTime<Utc>, merchant_id: u32,
) -> ChargeBuyerModel {
    let buyer_usr_id = 960u32;
    let charge_dlines: Vec<UTestChargeLineRawData> = vec![
        (merchant_id, ProductType::Item, 8299, (325, 1), (3250, 1), 10, (0, 0), (0, 0), 0, 0),
        (merchant_id, ProductType::Item, 8454, (909, 1), (9090, 1), 10, (0, 0), (0, 0), 0, 0),
        (merchant_id, ProductType::Package, 9913, (189, 1), (1890, 1), 10, (0, 0), (0, 0), 0, 0),
        (7788, ProductType::Package, 9914, (8392, 2), (83920, 2), 10, (0, 0), (0, 0), 0, 0),
    ];
    let paymethod = {
        let mut mthd = ut_default_charge_method_stripe(&charge_ctime);
        if let Charge3partyModel::Stripe(s) = &mut mthd {
            s.payment_state = StripeCheckoutPaymentStatusModel::paid;
        }
        mthd
    };
    let currency_snapshot = {
        let iter = [
            (buyer_usr_id, CurrencyDto::TWD, (3187i64, 2u32)),
            (merchant_id, CurrencyDto::IDR, (125021, 1)),
        ]
        .map(|(usr_id, label, ratescalar)| {
            let rate = Decimal::new(ratescalar.0, ratescalar.1);
            let obj = OrderCurrencySnapshot { label, rate };
            (usr_id, obj)
        });
        HashMap::from_iter(iter)
    };
    ut_setup_buyer_charge(
        buyer_usr_id, charge_ctime, mock_oid.to_string(),
        BuyerPayInState::OrderAppSynced(charge_ctime),
        paymethod, charge_dlines, currency_snapshot,
    )
} // end of fn ut_setup_buyer_charge_inner

#[rustfmt::skip]
fn ut_setup_order_refund_model(
    oid: &str, merchant_id: u32, time_base: DateTime<Utc>,
    d_lines: Vec<(u64, ProductType, i64, (i64,u32), (i64,u32), u32)>,
) -> OrderRefundModel {
    let rfnd_dtos = d_lines.into_iter()
        .map(|d| OrderLineReplicaRefundDto {
            seller_id: merchant_id, product_id: d.0, product_type: d.1,
            create_time: (time_base - Duration::minutes(d.2)).to_rfc3339() ,
            amount: PayAmountDto {
                unit: Decimal::new(d.3.0, d.3.1).to_string(),
                total: Decimal::new(d.4.0, d.4.1).to_string(),
            },
            qty: d.5,
        })
        .collect::<Vec<_>>();
    OrderRefundModel::try_from((oid.to_string(), rfnd_dtos)).unwrap()
}

#[rustfmt::skip]
fn ut_verify_cmplt_resp(
    time_base: DateTime<Utc>,
    rline: RefundCompletionOlineRespDto,
    expect_data_selector: fn(u64, ProductType, i64) -> (i64, u32, u32, u32),
) {
    let RefundCompletionOlineRespDto {product_type, product_id, time_issued, mut reject, approval} = rline;
    let expect = {
        let t_diff = (time_base - time_issued).num_minutes();
        let (amt_tot, qty_aprv, qty_rej_damage, qty_rej_fraud) =
            expect_data_selector(product_id, product_type, t_diff);
        let amt_tot = Decimal::new(amt_tot, 1);
        (amt_tot, qty_aprv, qty_rej_damage, qty_rej_fraud)
    };
    let actual = (
        Decimal::from_str(approval.amount_total.as_str()).unwrap(),
        approval.quantity,
        reject.remove(&RefundRejectReasonDto::Damaged).unwrap_or(0),
        reject.remove(&RefundRejectReasonDto::Fraudulent).unwrap_or(0),
    );
    assert_eq!(actual, expect);
}

#[rustfmt::skip]
#[actix_web::test]
async fn cmplt_req_done_all() {
    let time_base = Local::now().to_utc();
    let mock_oid = "d003bea7";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "WallMarrT", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(100)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_charge_ms = {
        let charge_m0 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(49), mock_merchant_id,
        );
        let charge_m1 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(88), mock_merchant_id,
        );
        vec![charge_m0, charge_m1]
    };
    let mock_rfnd_req_m = ut_setup_order_refund_model(
        mock_oid, mock_merchant_id, time_base,
        vec![
            (8299, ProductType::Item, 19, (325, 1), (325, 1), 1),
            (8299, ProductType::Item, 29, (325, 1), (1950, 1), 6),
            (8454, ProductType::Item, 39, (909, 1), (6363, 1), 7),
            (8454, ProductType::Item, 49, (909, 1), (7272, 1), 8),
        ],
    );
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(
        time_base,
        vec![
            (8299, ProductType::Item, 19, 0,    0, 1, 0),
            (8299, ProductType::Item, 29, 650,  2, 0, 4),
            (8454, ProductType::Item, 39, 6363, 7, 0, 0),
            (8454, ProductType::Item, 49, 4545, 5, 2, 1),
        ]
    );
    let repo_ch = ut_setup_repo_charge(Some(mock_charge_ms), Some(Ok(())));
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(Some(mock_rfnd_req_m));
    let processors = ut_setup_processor(Some(vec![false, false]));
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_ok());
    let data_selector = |prod_id:u64, prod_typ:ProductType, t_diff:i64| -> (i64,u32,u32,u32) {
        match (prod_id, prod_typ, t_diff) {
            (8299, ProductType::Item, 19) => (0  ,  0, 1, 0),
            (8299, ProductType::Item, 29) => (650,  2, 0, 4),
            (8454, ProductType::Item, 39) => (6363, 7, 0, 0),
            (8454, ProductType::Item, 49) => (4545, 5, 2, 1),
            _others => (-9999, 9999, 9999, 9999),
        }
    };
    if let Ok((cmplt_resp, errs3pty)) = result {
        assert!(errs3pty.is_empty());
        assert_eq!(cmplt_resp.lines.len(), 4);
        cmplt_resp.lines.into_iter()
            .map(|rline| ut_verify_cmplt_resp(time_base, rline, data_selector))
            .count();
    }
} // end of fn cmplt_req_done_all

#[rustfmt::skip]
#[actix_web::test]
async fn cmplt_req_done_partial() {
    let time_base = Local::now().to_utc();
    let mock_oid = "a01b738f";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "StarBark", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(99)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_charge_ms = {
        let charge_m0 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(69), mock_merchant_id,
        );
        let charge_m1 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(18), mock_merchant_id,
        );
        vec![charge_m0, charge_m1]
    };
    // Note this application does not verify whether quantity in each refund line
    // exceeds the quantity in original order line, this should be tested in
    // order-processing application
    let mock_rfnd_req_m = ut_setup_order_refund_model(
        mock_oid, mock_merchant_id, time_base,
        vec![
            (8299, ProductType::Item, 19, (325, 1), (2925, 1), 9),
            (8299, ProductType::Item, 29, (325, 1), (2600, 1), 8),
            (8454, ProductType::Item, 39, (909, 1), (6363, 1), 7),
            (8454, ProductType::Item, 49, (909, 1), (1818, 1), 2),
        ],
    );
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(
        time_base,
        vec![
            (8299, ProductType::Item, 19, 325,   1, 4, 2),
            (8299, ProductType::Item, 29, 1625,  5, 0, 1),
            (8454, ProductType::Item, 39, 0,     0, 2, 3),
            (8454, ProductType::Item, 49, 1818,  2, 0, 0),
        ]
    );
    let repo_ch = ut_setup_repo_charge(Some(mock_charge_ms), Some(Ok(())));
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(Some(mock_rfnd_req_m));
    let processors = ut_setup_processor(Some(vec![false, false]));
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_ok());
    let data_selector = |prod_id:u64, prod_typ:ProductType, t_diff:i64| -> (i64,u32,u32,u32) {
        match (prod_id, prod_typ, t_diff) {
            (8299, ProductType::Item, 19) => (325,   1, 4, 2),
            (8299, ProductType::Item, 29) => (1625,  5, 0, 1),
            (8454, ProductType::Item, 39) => (0,     0, 2, 3),
            (8454, ProductType::Item, 49) => (1818,  2, 0, 0),
            _others => (-9999, 9999, 9999, 9999),
        }
    };
    if let Ok((cmplt_resp, errs3pty)) = result {
        assert!(errs3pty.is_empty());
        assert_eq!(cmplt_resp.lines.len(), 4);
        cmplt_resp.lines.into_iter()
            .map(|rline| ut_verify_cmplt_resp(time_base, rline, data_selector))
            .count();
    }
} // end of cmplt_req_done_partial

#[rustfmt::skip]
#[actix_web::test]
async fn cmplt_req_done_with_processor_error() {
    let time_base = Local::now().to_utc();
    let mock_oid = "d003bea7";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "WallMarrT", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(100)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_charge_ms = {
        let charge_m0 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(49), mock_merchant_id,
        );
        let charge_m1 = ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(88), mock_merchant_id,
        );
        vec![charge_m0, charge_m1]
    };
    let mock_rfnd_req_m = ut_setup_order_refund_model(
        mock_oid, mock_merchant_id, time_base,
        vec![
            (8299, ProductType::Item, 19, (325, 1), (3900, 1), 12),
            (8299, ProductType::Item, 29, (325, 1), (650,  1), 2),
            (8299, ProductType::Item, 39, (325, 1), (1300, 1), 4),
            (8454, ProductType::Item, 49, (909, 1), (6363, 1), 7),
            (8454, ProductType::Item, 59, (909, 1), (7272, 1), 8),
        ],
    );
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(
        time_base,
        vec![
            (8299, ProductType::Item, 19, 3575, 11, 1, 0),
            (8299, ProductType::Item, 29,  650,  2, 0, 0),
            (8299, ProductType::Item, 39,  975,  3, 0, 1),
            (8454, ProductType::Item, 49, 5454,  6, 1, 0),
            (8454, ProductType::Item, 59, 6363,  7, 0, 1),
        ]
    );
    let repo_ch = ut_setup_repo_charge(Some(mock_charge_ms), Some(Ok(())));
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(Some(mock_rfnd_req_m));
    let processors = ut_setup_processor(Some(vec![false, true]));
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_ok());
    let data_selector = |prod_id:u64, prod_typ:ProductType, t_diff:i64| -> (i64,u32,u32,u32) {
        match (prod_id, prod_typ, t_diff) {
            (8299, ProductType::Item, 19) => (3250, 10, 1, 0),
            (8299, ProductType::Item, 39) => (0,     0, 0, 1),
            (8454, ProductType::Item, 49) => (5454,  6, 1, 0),
            (8454, ProductType::Item, 59) => (3636,  4, 0, 1),
            _others => (-9999, 9999, 9999, 9999),
        } // this is another partial completion case due to 3rd-party error
    };
    if let Ok((cmplt_resp, mut errs3pty)) = result {
        assert_eq!(errs3pty.len(), 1);
        let err3pty = errs3pty.remove(0);
        if let AppProcessorErrorReason::InvalidMethod(s) = err3pty.reason {
            assert_eq!(s.as_str(), "unit-test");
        } else {
            assert!(false);
        }
        assert_eq!(cmplt_resp.lines.len(), 4);
        cmplt_resp.lines.into_iter()
            .map(|rline| ut_verify_cmplt_resp(time_base, rline, data_selector))
            .count();
    }
} // end of fn cmplt_req_done_with_processor_error

#[rustfmt::skip]
#[actix_web::test]
async fn missing_charge_ids() {
    let time_base = Local::now().to_utc();
    let mock_oid = "d003bea7";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "TeSLaA", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(100)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(time_base, vec![]);
    let repo_ch = ut_setup_repo_charge(None, None);
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(None);
    let processors = ut_setup_processor(None);
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_err());
    if let Err(FinalizeRefundUcError::MissingChargeId(oid)) = result {
        assert_eq!(oid.as_str(), mock_oid);
    } else {
        assert!(false);
    }
} // end of fn missing_charge_ids

#[rustfmt::skip]
#[actix_web::test]
async fn resolve_failure_repo_refund() {
    let time_base = Local::now().to_utc();
    let mock_oid = "d003bea7";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "NVDA", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(100)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_charge_ms = vec![ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(49), mock_merchant_id,
        )];
    let mock_rfnd_req_m = ut_setup_order_refund_model(
        mock_oid, mock_merchant_id, time_base,
        vec![(8299, ProductType::Item, 19, (325, 1), (650,  1), 2)],
    );
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(
        time_base,
        vec![(8299, ProductType::Item, 19, 3250, 10, 0, 0)]
    );
    let repo_ch = ut_setup_repo_charge(Some(mock_charge_ms), None);
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(Some(mock_rfnd_req_m));
    let processors = ut_setup_processor(None);
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_err());
    if let Err(FinalizeRefundUcError::DataStore(e)) = result {
        assert_eq!(e.code, AppErrorCode::InvalidInput);
        if let AppRepoErrorDetail::RefundResolution(mut mes) = e.detail {
            assert_eq!(mes.len(), 1);
            let me = mes.remove(0);
            if let RefundModelError::QtyInsufficient { pid, num_avail, num_req } = me {
                assert_eq!(pid.store_id, mock_merchant_id);
                assert_eq!(pid.product_type, ProductType::Item);
                assert_eq!(pid.product_id, 8299);
                assert_eq!(num_req, 10);
                assert_eq!(num_avail, 2);
            } else {
                assert!(false);
            }
        } else {
            assert!(false);
        }
    } else {
        assert!(false);
    }
} // end of fn resolve_failure_repo_refund

#[rustfmt::skip]
#[actix_web::test]
async fn update_failure_chargeline() {
    let time_base = Local::now().to_utc();
    let mock_oid = "d003bea7";
    let mock_merchant_id = 127u32;
    let mock_staff_usr_id = 1551u32;
    let mock_merchant_profile = {
        let prof_dto = ut_setup_storeprofile_dto(
            "NVDA", mock_staff_usr_id, vec![mock_staff_usr_id],
            time_base - Duration::days(100)
        );
        MerchantProfileModel::try_from((mock_merchant_id , &prof_dto)).unwrap()
    };
    let mock_charge_ms = vec![ut_setup_buyer_charge_inner(
            mock_oid, time_base - Duration::minutes(49), mock_merchant_id,
        )];
    let mock_repo_err = AppRepoError {
        fn_label: AppRepoErrorFnLabel::UpdateChargeLinesRefund,
        code: AppErrorCode::RemoteDbServerFailure,
        detail: AppRepoErrorDetail::DatabaseExec("unit-test".to_string())
    };
    let mock_rfnd_req_m = ut_setup_order_refund_model(
        mock_oid, mock_merchant_id, time_base,
        vec![(8299, ProductType::Item, 19, (325, 1), (1625,  1), 5)],
    );
    let mock_cmplt_req = ut_setup_refund_cmplt_dto(
        time_base,
        vec![(8299, ProductType::Item, 19, 1300, 4, 1, 0)]
    );
    let repo_ch = ut_setup_repo_charge(Some(mock_charge_ms), Some(Err(mock_repo_err)));
    let repo_mc = ut_setup_repo_merchant(Some(mock_merchant_profile));
    let repo_rfd = ut_setup_repo_refund(Some(mock_rfnd_req_m));
    let processors = ut_setup_processor(Some(vec![false]));
    let uc = FinalizeRefundUseCase { repo_ch, repo_mc, repo_rfd, processors };
    let result = uc.execute(
        mock_oid.to_string(), mock_merchant_id,
        mock_staff_usr_id, mock_cmplt_req
    ).await;
    assert!(result.is_err());
    if let Err(FinalizeRefundUcError::DataStore(e)) = result {
        assert_eq!(e.code, AppErrorCode::RemoteDbServerFailure);
        if let AppRepoErrorDetail::DatabaseExec(s) = e.detail {
            assert_eq!(s.as_str(), "unit-test");
        } else {
            assert!(false);
        }
    } else {
        assert!(false);
    }
} // end of fn update_failure_chargeline
