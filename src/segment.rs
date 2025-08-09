use crate::serialization::Pickleable;
use anyhow::Result;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use risc0_zkvm::{ProverOpts, get_prover_server};
use risc0_zkvm::sha::Digestible;
use serde::{Deserialize, Serialize};

#[pyclass(module = "pyr0")]
#[derive(Serialize, Deserialize, Clone)]
pub struct Segment {
    segment: Option<risc0_zkvm::Segment>,
}

impl Segment {
    pub fn new(segment: risc0_zkvm::Segment) -> Self {
        Self {
            segment: Some(segment),
        }
    }

    pub fn prove(&self, verifier_context: &risc0_zkvm::VerifierContext) -> Result<SegmentReceipt> {
        // In RISC Zero 1.2, proving is done through the prover server
        let prover = get_prover_server(&ProverOpts::default())?;
        let receipt = prover.prove_segment(verifier_context, &self.segment.as_ref().unwrap())?;
        Ok(SegmentReceipt::new(receipt))
    }
}

impl Pickleable for Segment {}

#[pymethods]
impl Segment {
    #[new]
    fn new_init() -> Self {
        Self { segment: None }
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.to_bytes(py)
    }

    fn __setstate__(&mut self, py: Python<'_>, state: PyObject) -> PyResult<()> {
        *self = Self::from_bytes(state, py)?;
        Ok(())
    }
}

#[pyclass(module = "pyr0")]
#[derive(Serialize, Deserialize, Clone)]
pub struct SegmentReceipt {
    segment_receipt: Option<risc0_zkvm::SegmentReceipt>,
}

impl SegmentReceipt {
    pub fn new(segment_receipt: risc0_zkvm::SegmentReceipt) -> Self {
        Self {
            segment_receipt: Some(segment_receipt),
        }
    }

    pub fn get_segment_receipt_ref(&self) -> &risc0_zkvm::SegmentReceipt {
        &self.segment_receipt.as_ref().unwrap()
    }
}

impl Pickleable for SegmentReceipt {}

#[pymethods]
impl SegmentReceipt {
    #[new]
    fn new_init() -> Self {
        Self {
            segment_receipt: None,
        }
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.to_bytes(py)
    }

    fn __setstate__(&mut self, py: Python<'_>, state: PyObject) -> PyResult<()> {
        *self = Self::from_bytes(state, py)?;
        Ok(())
    }
    
    /// Get the journal (public outputs) as bytes
    pub fn journal_bytes<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
        let _receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        // In RISC Zero 1.2, we need to get the journal from the claim
        // For now, return empty bytes as the API has changed
        // TODO: Figure out how to extract journal from SegmentReceipt in 1.2
        Ok(pyo3::types::PyBytes::new(py, &[]))
    }
    
    /// Cryptographically verifies the segment seal against its embedded claim.
    /// Note: This does NOT check success exit code or expected image ID.
    /// For full verification including exit code and image ID checks, use the top-level Receipt.verify() method.
    #[pyo3(signature = ())]
    pub fn verify_integrity(&self) -> PyResult<()> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        let verifier_ctx = risc0_zkvm::VerifierContext::default();
        
        receipt.verify_integrity_with_context(&verifier_ctx)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Verification failed: {}", e)))
    }
    
    /// Legacy verify method - calls verify_integrity
    /// Deprecated: Use verify_integrity() instead
    pub fn verify(&self) -> PyResult<bool> {
        match self.verify_integrity() {
            Ok(()) => Ok(true),
            Err(_) => Ok(false),
        }
    }
    
    /// Get the exit code from the receipt's claim
    pub fn get_exit_code(&self) -> PyResult<u32> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        // Get exit code based on the ExitCode enum
        use risc0_binfmt::ExitCode;
        match &receipt.claim.exit_code {
            ExitCode::Halted(code) => Ok(*code),
            ExitCode::Paused(code) => Ok(*code),
            ExitCode::SystemSplit => Ok(0), // System split doesn't have a code
            ExitCode::SessionLimit => Ok(0), // Session limit doesn't have a code
        }
    }
    
    /// Get the program ID (image ID) from the receipt
    pub fn program_id<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        // The program ID is the digest of the pre-execution SystemState
        let digest = receipt.claim.pre.digest();
        Ok(PyBytes::new(py, digest.as_bytes()))
    }
}
