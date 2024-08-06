mod create_charge;

use std::boxed::Box;
use std::result::Result;
use std::sync::Mutex;

use async_trait::async_trait;
use chrono::{DateTime, Utc};

use ecommerce_common::error::AppErrorCode;
use ecommerce_common::model::order::BillingModel;

use payment::adapter::cache::{AbstractOrderSyncLockCache, OrderSyncLockError};
use payment::adapter::processor::{
    AbstractPaymentProcessor, AppProcessorError, AppProcessorErrorReason, AppProcessorPayInResult,
};
use payment::adapter::repository::{
    AbstractChargeRepo, AppRepoError, AppRepoErrorDetail, AppRepoErrorFnLabel,
};
use payment::adapter::rpc::{
    AbsRpcClientContext, AbstractRpcClient, AbstractRpcContext, AbstractRpcPublishEvent,
    AppRpcClientRequest, AppRpcCtxError, AppRpcReply,
};
use payment::api::web::dto::PaymentMethodReqDto;
use payment::model::{
    Charge3partyModel, ChargeBuyerMetaModel, ChargeBuyerModel, ChargeLineBuyerModel,
    OrderLineModelSet,
};

struct MockChargeRepo {
    _expect_unpaid_olines: Mutex<Option<Result<Option<OrderLineModelSet>, AppRepoError>>>,
    _create_order_result: Mutex<Option<Result<(), AppRepoError>>>,
    _create_charge_result: Mutex<Option<Result<(), AppRepoError>>>,
}

#[async_trait]
impl AbstractChargeRepo for MockChargeRepo {
    async fn get_unpaid_olines(
        &self,
        _usr_id: u32,
        _oid: &str,
    ) -> Result<Option<OrderLineModelSet>, AppRepoError> {
        let mut g = self._expect_unpaid_olines.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
    async fn create_order(
        &self,
        _olines: &OrderLineModelSet,
        _billing: &BillingModel,
    ) -> Result<(), AppRepoError> {
        let mut g = self._create_order_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
    async fn create_charge(&self, _cline_set: ChargeBuyerModel) -> Result<(), AppRepoError> {
        let mut g = self._create_charge_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
    async fn fetch_charge_meta(
        &self,
        _usr_id: u32,
        _create_time: DateTime<Utc>,
    ) -> Result<Option<ChargeBuyerMetaModel>, AppRepoError> {
        Err(AppRepoError {
            fn_label: AppRepoErrorFnLabel::FetchChargeMeta,
            code: AppErrorCode::NotImplemented,
            detail: AppRepoErrorDetail::Unknown,
        })
    }
    async fn fetch_all_charge_lines(
        &self,
        _usr_id: u32,
        _create_time: DateTime<Utc>,
    ) -> Result<Vec<ChargeLineBuyerModel>, AppRepoError> {
        Err(AppRepoError {
            fn_label: AppRepoErrorFnLabel::FetchAllChargeLines,
            code: AppErrorCode::NotImplemented,
            detail: AppRepoErrorDetail::Unknown,
        })
    }
    async fn update_charge_progress(
        &self,
        _meta: ChargeBuyerMetaModel,
    ) -> Result<(), AppRepoError> {
        Err(AppRepoError {
            fn_label: AppRepoErrorFnLabel::UpdateChargeProgress,
            code: AppErrorCode::NotImplemented,
            detail: AppRepoErrorDetail::Unknown,
        })
    }
} // end of impl MockChargeRepo

struct MockOrderSyncLockCache {
    _acquire_result: Mutex<Option<Result<bool, OrderSyncLockError>>>,
    _release_result: Mutex<Option<Result<(), OrderSyncLockError>>>,
}

#[async_trait]
impl AbstractOrderSyncLockCache for MockOrderSyncLockCache {
    async fn acquire(&self, _usr_id: u32, _oid: &str) -> Result<bool, OrderSyncLockError> {
        let mut g = self._acquire_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
    async fn release(&self, _usr_id: u32, _oid: &str) -> Result<(), OrderSyncLockError> {
        let mut g = self._release_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
}

struct MockRpcContext {
    _acquire_result: Mutex<Option<Result<Box<dyn AbstractRpcClient>, AppRpcCtxError>>>,
}
struct MockRpcClient {
    _send_req_result: Mutex<Option<Result<Box<dyn AbstractRpcPublishEvent>, AppRpcCtxError>>>,
}
struct MockRpcPublishEvent {
    _recv_resp_result: Mutex<Option<Result<AppRpcReply, AppRpcCtxError>>>,
}

impl AbstractRpcContext for MockRpcContext {}

#[async_trait]
impl AbsRpcClientContext for MockRpcContext {
    async fn acquire(&self) -> Result<Box<dyn AbstractRpcClient>, AppRpcCtxError> {
        let mut g = self._acquire_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }
}

#[async_trait]
impl AbstractRpcClient for MockRpcClient {
    async fn send_request(
        mut self: Box<Self>,
        _props: AppRpcClientRequest,
    ) -> Result<Box<dyn AbstractRpcPublishEvent>, AppRpcCtxError> {
        let mut g = self._send_req_result.lock().unwrap();
        let evt = g.take().unwrap();
        evt
    }
}
#[async_trait]
impl AbstractRpcPublishEvent for MockRpcPublishEvent {
    async fn receive_response(&mut self) -> Result<AppRpcReply, AppRpcCtxError> {
        let mut g = self._recv_resp_result.lock().unwrap();
        let mock_result = g.take().unwrap();
        mock_result
    }
}

struct MockPaymentProcessor {
    _payin_start_result:
        Mutex<Option<Result<(AppProcessorPayInResult, Charge3partyModel), AppProcessorError>>>,
}

#[async_trait]
impl AbstractPaymentProcessor for MockPaymentProcessor {
    async fn pay_in_start(
        &self,
        _charge_buyer: &ChargeBuyerModel,
        _req_mthd: PaymentMethodReqDto,
    ) -> Result<(AppProcessorPayInResult, Charge3partyModel), AppProcessorError> {
        let mut g = self._payin_start_result.lock().unwrap();
        let out = g.take().unwrap();
        out
    }

    async fn pay_in_progress(
        &self,
        _meta: &ChargeBuyerMetaModel,
    ) -> Result<Charge3partyModel, AppProcessorError> {
        Err(AppProcessorError {
            reason: AppProcessorErrorReason::NotImplemented,
        })
    }
}
