use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};

use risc0_zkvm::{
    Receipt as RiscZeroReceipt,
    MaybePruned,
    ExitCode,
};
use risc0_zkvm::sha::{Digest, Digestible};

#[pyclass(module = "pyr0")]
#[derive(Clone)]
pub struct Receipt {
    pub(crate) inner: RiscZeroReceipt,
}

impl Receipt {
    pub fn from_risc0(receipt: RiscZeroReceipt) -> Self {
        Self { inner: receipt }
    }
}

#[pymethods]
impl Receipt {
    #[getter]
    pub fn journal(&self) -> PyResult<Vec<u8>> {
        Ok(self.inner.journal.bytes.clone())
    }

    #[getter]
    pub fn exit_code(&self) -> PyResult<u32> {
        let claim_pruned = self.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to decode claim: {e}")))?;
        
        let claim = match claim_pruned.as_value() {
            Ok(claim) => claim,
            Err(_) => return Err(PyErr::new::<PyRuntimeError, _>("Claim is pruned")),
        };
        
        let code = match claim.exit_code {
            ExitCode::Halted(user) | ExitCode::Paused(user) => user,
            ExitCode::SystemSplit | ExitCode::SessionLimit => u32::MAX,
        };
        Ok(code)
    }

    /// Pre-state digest claimed by the receipt (often used as an image-id-like value).
    #[getter]
    pub fn program_id(&self) -> PyResult<Vec<u8>> {
        let claim_pruned = self.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to decode claim: {e}")))?;
        
        let claim = match claim_pruned.as_value() {
            Ok(claim) => claim,
            Err(_) => return Err(PyErr::new::<PyRuntimeError, _>("Claim is pruned")),
        };
        
        let digest = match &claim.pre {
            MaybePruned::Value(state) => state.digest(),
            MaybePruned::Pruned(d)    => d.clone(),
        };
        Ok(digest.as_bytes().to_vec())
    }

    /// Verify the receipt against a trusted image ID
    /// 
    /// SECURITY: Always provide the image_id from a trusted source
    /// (e.g., from Image.id or a compile-time constant).
    /// Never derive it from the receipt itself!
    pub fn verify(&self, image_id_bytes: &Bound<'_, PyAny>) -> PyResult<()> {
        let bytes: Vec<u8> = image_id_bytes.extract()?;
        let image_id = Digest::try_from(bytes.as_slice())
            .map_err(|_| PyErr::new::<PyValueError, _>("image_id must be 32 bytes"))?;
        self.inner.verify(image_id)
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Verification failed: {e}")))
    }
    
    /// Deprecated: Use verify() instead
    /// This method is kept for backward compatibility but is identical to verify()
    pub fn verify_with_image_id(&self, image_id_bytes: &Bound<'_, PyAny>) -> PyResult<()> {
        self.verify(image_id_bytes)
    }

    pub fn __repr__(&self) -> String {
        format!("Receipt(journal_len={}, seal_size={})",
                self.inner.journal.bytes.len(),
                self.inner.seal_size())
    }
}
