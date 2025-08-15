use anyhow::Result;
use pyo3::prelude::*;
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


#[pymethods]
impl Segment {
    #[new]
    fn new_init() -> Self {
        Self { segment: None }
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


#[pymethods]
impl SegmentReceipt {
    #[new]
    fn new_init() -> Self {
        Self {
            segment_receipt: None,
        }
    }

    
    /// Get the journal (public outputs) as bytes
    #[getter]
    pub fn journal(&self) -> PyResult<Vec<u8>> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        // In RISC Zero 1.2, journal is in receipt.claim.output.journal
        // The fields are wrapped in MaybePruned, so we need to unwrap them
        let output_opt = receipt.claim.output.as_value()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Journal output is pruned"))?;
        
        match output_opt.as_ref() {
            Some(output) => {
                // Get the journal bytes from the output
                let journal_bytes = output.journal.as_value()
                    .map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Journal is pruned"))?;
                Ok(journal_bytes.clone())
            }
            None => {
                // Guest didn't write a journal, return empty bytes
                Ok(vec![])
            }
        }
    }
    
    /// Cryptographically verifies the segment seal against its embedded claim.
    #[pyo3(signature = ())]
    pub fn verify(&self) -> PyResult<()> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        let verifier_ctx = risc0_zkvm::VerifierContext::default();
        
        receipt.verify_integrity_with_context(&verifier_ctx)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Verification failed: {}", e)))
    }
    
    
    /// Get the exit code from the receipt's claim
    #[getter]
    pub fn exit_code(&self) -> PyResult<u32> {
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
    #[getter]
    pub fn program_id(&self) -> PyResult<Vec<u8>> {
        let receipt = self.segment_receipt.as_ref()
            .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Receipt is None"))?;
        
        // The program ID is the digest of the pre-execution SystemState
        let digest = receipt.claim.pre.digest();
        Ok(digest.as_bytes().to_vec())
    }
}
