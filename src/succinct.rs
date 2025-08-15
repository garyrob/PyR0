use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[pyclass(module = "pyr0")]
#[derive(Clone, Serialize, Deserialize)]
pub struct SuccinctReceipt {
    succinct_receipt: Option<risc0_zkvm::SuccinctReceipt<risc0_zkvm::ReceiptClaim>>,
}

impl SuccinctReceipt {
    pub fn new(succinct_receipt: risc0_zkvm::SuccinctReceipt<risc0_zkvm::ReceiptClaim>) -> Self {
        Self {
            succinct_receipt: Some(succinct_receipt),
        }
    }

    pub fn get_succinct_receipt_ref(&self) -> &risc0_zkvm::SuccinctReceipt<risc0_zkvm::ReceiptClaim> {
        &self.succinct_receipt.as_ref().unwrap()
    }
}


#[pymethods]
impl SuccinctReceipt {
    #[new]
    fn new_init() -> Self {
        Self {
            succinct_receipt: None,
        }
    }

}
