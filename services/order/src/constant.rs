use std::hash::Hash;
use std::str::FromStr;

use crate::error::{AppError, AppErrorCode};
use crate::WebApiHdlrLabel;

pub mod app_meta {
    pub const LABAL: &str = "order";
    pub const MACHINE_CODE: u8 = 1;
    // TODO, machine code to UUID generator should be configurable
    pub const RESOURCE_QUOTA_AP_CODE: u8 = 4;
}

pub const ENV_VAR_SYS_BASE_PATH: &str = "SYS_BASE_PATH";
pub const ENV_VAR_SERVICE_BASE_PATH: &str = "SERVICE_BASE_PATH";
pub const ENV_VAR_CONFIG_FILE_PATH: &str = "CONFIG_FILE_PATH";

pub const EXPECTED_ENV_VAR_LABELS: [&str; 3] = [
    ENV_VAR_SYS_BASE_PATH,
    ENV_VAR_SERVICE_BASE_PATH,
    ENV_VAR_CONFIG_FILE_PATH,
];

pub mod limit {
    pub const MAX_ITEMS_STORED_PER_MODEL: u32 = 2200u32;
    pub const MAX_ORDER_LINES_PER_REQUEST: usize = 65535;
    pub const MAX_DB_CONNECTIONS: u32 = 10000u32;
    pub const MAX_SECONDS_DB_IDLE: u16 = 600u16;
    pub const MIN_SECS_INTVL_REQ: u16 = 3;
    pub const MAX_NUM_CARTS_PER_USER: u8 = 5; // TODO, configurable in user-mgt app
}

pub(crate) mod api {
    use super::{app_meta, AppError, AppErrorCode, WebApiHdlrLabel};
    use std::result::Result as DefaultResult;

    #[allow(non_camel_case_types)]
    pub(crate) struct web {}

    impl web {
        pub(crate) const ADD_PRODUCT_POLICY: WebApiHdlrLabel = "modify_product_policy";
        pub(crate) const CREATE_NEW_ORDER: WebApiHdlrLabel = "create_new_order";
        pub(crate) const ACCESS_EXISTING_ORDER: WebApiHdlrLabel = "access_existing_order";
        pub(crate) const RETURN_OLINES_REQ: WebApiHdlrLabel = "return_lines_request";
        pub(crate) const RETRIEVE_CART_LINES: WebApiHdlrLabel = "retrieve_cart_lines";
        pub(crate) const MODIFY_CART_LINES: WebApiHdlrLabel = "modify_cart_lines";
        pub(crate) const DISCARD_CART: WebApiHdlrLabel = "discard_cart";
    }

    #[allow(non_camel_case_types)]
    pub(crate) struct rpc {}

    impl rpc {
        pub(crate) const EDIT_PRODUCT_PRICE: WebApiHdlrLabel = "update_store_products";
        pub(crate) const STOCK_LEVEL_EDIT: WebApiHdlrLabel = "stock_level_edit";
        pub(crate) const STOCK_RETURN_CANCELLED: WebApiHdlrLabel = "stock_return_cancelled";
        pub(crate) const ORDER_RSV_READ_INVENTORY: WebApiHdlrLabel =
            "order_reserved_replica_inventory";
        pub(crate) const ORDER_RSV_READ_PAYMENT: WebApiHdlrLabel = "order_reserved_replica_payment";
        pub(crate) const ORDER_RET_READ_REFUND: WebApiHdlrLabel = "order_returned_replica_refund";
        pub(crate) const ORDER_RSV_UPDATE_PAYMENT: WebApiHdlrLabel =
            "order_reserved_update_payment";
        pub(crate) const ORDER_RSV_DISCARD_UNPAID: WebApiHdlrLabel =
            "order_reserved_discard_unpaid";

        pub(crate) fn extract_handler_label(path: &str) -> DefaultResult<&str, AppError> {
            let mut tokens = path.split('.').collect::<Vec<&str>>();
            if tokens.len() == 3 {
                Self::check_header_label(tokens.remove(0))?;
                Self::check_service_label(tokens.remove(0))?;
                let out = Self::check_hdlr_label(tokens.remove(0))?;
                Ok(out)
            } else {
                let detail = format!("incorrect-format, tokens-length:{}", tokens.len());
                Err(AppError {
                    code: AppErrorCode::InvalidInput,
                    detail: Some(detail),
                })
            }
        }
        fn check_header_label(label: &str) -> DefaultResult<(), AppError> {
            if label == "rpc" {
                Ok(())
            } else {
                let detail = format!("incorrect-header:{label}");
                Err(AppError {
                    code: AppErrorCode::InvalidInput,
                    detail: Some(detail),
                })
            }
        }
        fn check_service_label(label: &str) -> DefaultResult<(), AppError> {
            if label == app_meta::LABAL {
                Ok(())
            } else {
                let detail = format!("incorrect-service:{label}");
                Err(AppError {
                    code: AppErrorCode::InvalidInput,
                    detail: Some(detail),
                })
            }
        }
        fn check_hdlr_label(label: &str) -> DefaultResult<&str, AppError> {
            let valid_labels = [
                Self::EDIT_PRODUCT_PRICE,
                Self::STOCK_LEVEL_EDIT,
                Self::STOCK_RETURN_CANCELLED,
                Self::ORDER_RSV_READ_INVENTORY,
                Self::ORDER_RSV_READ_PAYMENT,
                Self::ORDER_RET_READ_REFUND,
                Self::ORDER_RSV_UPDATE_PAYMENT,
                Self::ORDER_RSV_DISCARD_UNPAID,
            ];
            if valid_labels.contains(&label) {
                Ok(label)
            } else {
                let detail = format!("incorrect-handler:{label}");
                Err(AppError {
                    code: AppErrorCode::InvalidInput,
                    detail: Some(detail),
                })
            }
        }
    } // end of inner-struct rpc
} // end of inner-mod api

pub(crate) const HTTP_CONTENT_TYPE_JSON: &str = "application/json";

// standard library hides the default implementation of the trait `PartialEq`
// somewhere in compiler code, the trait `Hash` seems to prefer the default
// code working with itself, it is needless to implement trait `PartialEq`
// for `ProductType` at here.
#[derive(Debug, Eq, PartialEq, Hash)]
pub enum ProductType {
    Item,
    Package,
    Unknown(u8),
}

impl From<u8> for ProductType {
    fn from(value: u8) -> Self {
        match value {
            1 => Self::Item,
            2 => Self::Package,
            _others => Self::Unknown(value),
        }
    }
}
impl From<ProductType> for u8 {
    fn from(value: ProductType) -> u8 {
        match value {
            ProductType::Unknown(v) => v,
            ProductType::Item => 1,
            ProductType::Package => 2,
        }
    }
}
impl Clone for ProductType {
    fn clone(&self) -> Self {
        match self {
            Self::Item => Self::Item,
            Self::Unknown(v) => Self::Unknown(*v),
            Self::Package => Self::Package,
        }
    }
}
impl FromStr for ProductType {
    type Err = AppError;
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s.parse::<u8>() {
            Ok(v) => Ok(Self::from(v)),
            Err(e) => {
                let detail = format!("product-type, actual:{}, error:{}", s, e);
                Err(Self::Err {
                    code: AppErrorCode::DataCorruption,
                    detail: Some(detail),
                })
            }
        }
    }
}

pub(crate) const REGEX_EMAIL_RFC5322: &str = r#"(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"#;

pub(crate) mod logging {
    use serde::Deserialize;

    #[allow(clippy::upper_case_acronyms)]
    #[derive(Deserialize)]
    pub enum Level {
        TRACE,
        DEBUG,
        INFO,
        WARNING,
        ERROR,
        FATAL,
    }

    #[allow(clippy::upper_case_acronyms)]
    #[derive(Deserialize)]
    #[serde(rename_all = "lowercase")]
    pub enum Destination {
        CONSOLE,
        LOCALFS,
    } // TODO, Fluentd
}
