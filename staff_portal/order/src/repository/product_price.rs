use std::sync::Arc;
use std::boxed::Box;
use std::result::Result as DefaultResult;
use std::collections::HashMap;

use async_trait::async_trait;
use chrono::DateTime;

use crate::AppDataStoreContext;
use crate::api::rpc::dto::ProductPriceDeleteDto;
use crate::datastore::{AbstInMemoryDStore, AppInMemFetchKeys};
use crate::error::{AppError, AppErrorCode};
use crate::model::{ProductPriceModelSet, ProductPriceModel};
use super::AbsProductPriceRepo;

const TABLE_LABEL: &'static str = "product_price";

enum InMemColIdx {Price, StartAfter, EndBefore, ProductId, ProductType, TotNumColumns}

impl Into<usize> for InMemColIdx {
    fn into(self) -> usize {
        match self {
            Self::Price => 0,
            Self::StartAfter => 1,
            Self::EndBefore => 2,
            Self::ProductId => 3,
            Self::ProductType => 4,
            Self::TotNumColumns => 5,
        }
    }
}

pub struct ProductPriceInMemRepo {
    datastore: Arc<Box<dyn AbstInMemoryDStore>>
}

#[async_trait]
impl AbsProductPriceRepo for ProductPriceInMemRepo {
    fn new(dstore:Arc<AppDataStoreContext>) -> DefaultResult<Box<dyn AbsProductPriceRepo>, AppError>
        where Self:Sized
    {
        match Self::_new(dstore) {
            Ok(rp) => Ok(Box::new(rp)),
            Err(e) => Err(e)
        }
    }
    async fn delete_all(&self, store_id:u32) -> Result<(), AppError>
    { Ok(()) }
    
    async fn delete(&self, store_id:u32, ids:ProductPriceDeleteDto) -> Result<(), AppError>
    { Ok(()) }

    async fn fetch(&self, store_id:u32, ids:Vec<(u8,u64)>) -> Result<ProductPriceModelSet, AppError>
    {
        let info = self.gen_id_keys(store_id, ids);
        let result_raw = self.datastore.fetch(info)?;
        let filtered = if let Some(t) = result_raw.get(TABLE_LABEL)
        { // TODO, reliability check
            t.into_iter().map(|(_key, row)| {
                let product_type = row.get::<usize>(InMemColIdx::ProductType.into())
                    .unwrap().parse().unwrap();
                let product_id = row.get::<usize>(InMemColIdx::ProductId.into())
                    .unwrap().parse().unwrap();
                let price = row.get::<usize>(InMemColIdx::Price.into())
                    .unwrap().parse().unwrap();
                let start_after = row.get::<usize>(InMemColIdx::StartAfter.into()).unwrap();
                let end_before  = row.get::<usize>(InMemColIdx::EndBefore.into()).unwrap();
                let start_after = DateTime::parse_from_rfc3339(start_after).unwrap().into();
                let end_before  = DateTime::parse_from_rfc3339(end_before).unwrap().into();
                ProductPriceModel {product_type, product_id, price,
                    start_after, end_before, is_create:false}
            }).collect()
        } else { Vec::new() };
        let obj = ProductPriceModelSet {store_id, items:filtered};
        Ok(obj)
    } // end of fn fetch

    async fn save(&self, ppset:ProductPriceModelSet) -> Result<(), AppError>
    {
        if ppset.store_id == 0 || ppset.items.is_empty() {
            return Err(AppError {code: AppErrorCode::EmptyInputData,
                detail:Some(format!("save ProductPriceModel"))  });
        }
        let kv_pairs = ppset.items.iter().map(|m| {
            let store_id_str = ppset.store_id.to_string();
            let pkey = format!("{}-{}-{}", store_id_str, m.product_type.to_string(),
                    m.product_id.to_string());
            // manually allocate space in advance, instead of `Vec::with_capacity`
            let mut row = (0..InMemColIdx::TotNumColumns.into()).map(
                |_n| String::new())  .collect::<Vec<String>>();
            let _ = [ // so the order of columns can be arbitrary
                (InMemColIdx::Price, m.price.to_string()),
                (InMemColIdx::ProductType, m.product_type.to_string()),
                (InMemColIdx::ProductId,  m.product_id.to_string()),
                (InMemColIdx::StartAfter, m.start_after.to_rfc3339()),
                (InMemColIdx::EndBefore,  m.end_before.to_rfc3339()),
            ].into_iter().map(|(idx, val)| {
                let idx:usize = idx.into();
                row[idx] = val;
            }).collect::<Vec<()>>();
            (pkey, row)
        });
        let rows = HashMap::from_iter(kv_pairs);
        let mut data = HashMap::new();
        data.insert(TABLE_LABEL.to_string(), rows);
        let _num = self.datastore.save(data)?;
        Ok(())
    } // end of fn save
} // end of impl ProductPriceInMemRepo

impl ProductPriceInMemRepo {
    pub fn _new(dstore:Arc<AppDataStoreContext>) -> DefaultResult<Self, AppError>
        where Self:Sized
    {
        if let Some(m) = &dstore.in_mem {
            m.create_table(TABLE_LABEL)?;
            let obj = Self { datastore: m.clone() };
            Ok(obj)
        } else {
            Err(AppError {code:AppErrorCode::MissingDataStore,
                detail: Some(format!("in-memory"))}  )
        }
    }
    fn gen_id_keys(&self, store_id:u32, ids:Vec<(u8,u64)>) -> AppInMemFetchKeys
    {
        let str_ids = ids.into_iter().map(|(_typ, _id)| {
            format!("{}-{}-{}", store_id.to_string(), _typ.to_string(), _id.to_string())
        }).collect();
        let mut h = HashMap::new();
        h.insert(TABLE_LABEL.to_string(), str_ids);
        h
    }
} // end of impl ProductPriceInMemRepo
