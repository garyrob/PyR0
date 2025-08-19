use pyo3::prelude::*;
use risc0_zkvm::sha::Digestible;

/// A claim represents what a receipt proves: an image ID executed with a specific journal
/// 
/// This is the core abstraction in RISC Zero - a receipt proves a claim about
/// program execution. Understanding claims is key to understanding composition.
#[pyclass(module = "pyr0")]
#[derive(Clone)]
pub struct Claim {
    /// The image ID of the program that was executed (32 bytes)
    #[pyo3(get)]
    pub image_id: Vec<u8>,
    
    /// The raw journal bytes that were committed during execution
    #[pyo3(get)]
    pub journal: Vec<u8>,
    
    /// The SHA-256 digest of the journal (32 bytes)
    /// This is what actually gets included in the claim
    #[pyo3(get)]
    pub journal_digest: Vec<u8>,
    
    /// The exit code of the program execution
    #[pyo3(get)]
    pub exit_code: u32,
}

#[pymethods]
impl Claim {
    /// Create a new Claim from components
    #[new]
    pub fn new(image_id: Vec<u8>, journal: Vec<u8>, exit_code: u32) -> PyResult<Self> {
        if image_id.len() != 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Image ID must be 32 bytes, got {}", image_id.len())
            ));
        }
        
        // Compute journal digest
        use risc0_zkvm::sha::Sha256;
        let journal_digest = risc0_zkvm::sha::Impl::hash_bytes(&journal);
        
        Ok(Claim {
            image_id,
            journal: journal.clone(),
            journal_digest: journal_digest.as_bytes().to_vec(),
            exit_code,
        })
    }
    
    /// Get the image ID as a hex string
    #[getter]
    pub fn image_id_hex(&self) -> String {
        hex::encode(&self.image_id)
    }
    
    /// Get the journal digest as a hex string
    #[getter]
    pub fn journal_digest_hex(&self) -> String {
        hex::encode(&self.journal_digest)
    }
    
    /// Check if this claim matches an expected image ID and journal
    pub fn matches(&self, image_id: Vec<u8>, journal: Vec<u8>) -> bool {
        self.image_id == image_id && self.journal == journal
    }
    
    /// Check if this claim indicates successful execution
    #[getter]
    pub fn is_success(&self) -> bool {
        self.exit_code == 0
    }
    
    pub fn __repr__(&self) -> String {
        format!(
            "Claim(image_id={}, journal_len={}, exit_code={})",
            &self.image_id_hex()[..8],
            self.journal.len(),
            self.exit_code
        )
    }
    
    pub fn __str__(&self) -> String {
        let exit_str = if self.exit_code == 0 { 
            "Success".to_string() 
        } else { 
            format!("Failed ({})", self.exit_code)
        };
        format!(
            "Claim:\n  Image ID: {}...\n  Journal: {} bytes\n  Exit: {}",
            &self.image_id_hex()[..16],
            self.journal.len(),
            exit_str
        )
    }
}

impl Claim {
    /// Create a Claim from a RISC Zero claim
    pub fn from_risc0_claim(
        claim: &risc0_zkvm::ReceiptClaim,
        journal_bytes: Vec<u8>
    ) -> PyResult<Self> {
        // Extract image ID from the claim's pre-state
        let image_id = match &claim.pre {
            risc0_zkvm::MaybePruned::Value(state) => state.digest(),
            risc0_zkvm::MaybePruned::Pruned(digest) => digest.clone(),
        };
        
        // Extract exit code
        let exit_code = match claim.exit_code {
            risc0_zkvm::ExitCode::Halted(code) => code,
            risc0_zkvm::ExitCode::Paused(code) => code,
            _ => u32::MAX, // System exit codes
        };
        
        // Compute journal digest
        use risc0_zkvm::sha::Sha256;
        let journal_digest = risc0_zkvm::sha::Impl::hash_bytes(&journal_bytes);
        
        Ok(Claim {
            image_id: image_id.as_bytes().to_vec(),
            journal: journal_bytes,
            journal_digest: journal_digest.as_bytes().to_vec(),
            exit_code,
        })
    }
}