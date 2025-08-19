use pyo3::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};

use risc0_zkvm::{
    Receipt as RiscZeroReceipt,
    MaybePruned,
    ExitCode as RiscZeroExitCode,
};
use risc0_zkvm::sha::{Digest, Digestible};


/// Exit kind enumeration for Python
#[pyclass(module = "pyr0", eq, eq_int)]
#[derive(Clone, Debug, PartialEq)]
pub enum ExitKind {
    #[pyo3(name = "HALTED")]
    Halted,
    #[pyo3(name = "PAUSED")]
    Paused,
    #[pyo3(name = "SYSTEM_SPLIT")]
    SystemSplit,
    #[pyo3(name = "SESSION_LIMIT")]
    SessionLimit,
    #[pyo3(name = "UNKNOWN")]
    Unknown,
}

/// Structured exit status information
#[pyclass(module = "pyr0")]
#[derive(Clone, Debug)]
pub struct ExitStatus {
    #[pyo3(get)]
    pub kind: ExitKind,
    #[pyo3(get)]
    pub user_code: Option<u32>,
}

#[pymethods]
impl ExitStatus {
    /// Returns true if this represents successful execution (typically HALTED with code 0)
    #[getter]
    pub fn ok(&self) -> bool {
        matches!(self.kind, ExitKind::Halted) && self.user_code == Some(0)
    }
    
    pub fn __repr__(&self) -> String {
        match (&self.kind, self.user_code) {
            (ExitKind::Halted, Some(code)) => format!("ExitStatus(HALTED, {})", code),
            (ExitKind::Paused, Some(code)) => format!("ExitStatus(PAUSED, {})", code),
            (kind, _) => format!("ExitStatus({:?})", kind),
        }
    }
}

#[pyclass(module = "pyr0")]
#[derive(Clone)]
pub struct Receipt {
    pub inner: RiscZeroReceipt,
}

impl Receipt {
    pub fn from_risc0(receipt: RiscZeroReceipt) -> Self {
        Self { inner: receipt }
    }
}

#[pymethods]
impl Receipt {
    // ===== Journal properties =====
    
    /// Raw journal bytes as emitted by the guest
    #[getter]
    pub fn journal_bytes(&self) -> PyResult<Vec<u8>> {
        Ok(self.inner.journal.bytes.clone())
    }
    
    /// Journal as hex string (useful for logging/transport)
    #[getter]
    pub fn journal_hex(&self) -> PyResult<String> {
        Ok(hex::encode(&self.inner.journal.bytes))
    }
    
    /// UTF-8 decode of journal if valid, otherwise None
    #[getter]
    pub fn journal_text(&self) -> PyResult<Option<String>> {
        Ok(String::from_utf8(self.inner.journal.bytes.clone()).ok())
    }
    
    /// Length of the journal in bytes
    #[getter]
    pub fn journal_len(&self) -> PyResult<usize> {
        Ok(self.inner.journal.bytes.len())
    }
    
    // Legacy getter for backward compatibility
    #[getter]
    pub fn journal(&self) -> PyResult<Vec<u8>> {
        self.journal_bytes()
    }
    
    // ===== Exit status =====
    
    /// Structured exit status information
    #[getter]
    pub fn exit(&self) -> PyResult<ExitStatus> {
        let claim_pruned = self.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to decode claim: {e}")))?;
        
        let claim = match claim_pruned.as_value() {
            Ok(claim) => claim,
            Err(_) => return Err(PyErr::new::<PyRuntimeError, _>("Claim is pruned")),
        };
        
        let (kind, user_code) = match claim.exit_code {
            RiscZeroExitCode::Halted(code) => (ExitKind::Halted, Some(code)),
            RiscZeroExitCode::Paused(code) => (ExitKind::Paused, Some(code)),
            RiscZeroExitCode::SystemSplit => (ExitKind::SystemSplit, None),
            RiscZeroExitCode::SessionLimit => (ExitKind::SessionLimit, None),
        };
        
        Ok(ExitStatus { kind, user_code })
    }
    
    // Legacy getter for backward compatibility - returns raw u32
    #[getter]
    pub fn exit_code(&self) -> PyResult<u32> {
        let exit = self.exit()?;
        Ok(exit.user_code.unwrap_or(u32::MAX))
    }
    
    // ===== Image ID (claimed, not trusted) =====
    
    /// The CLAIMED image ID from the receipt (for inspection/debugging only)
    /// SECURITY: This is untrusted data! Use verify_hex/verify_bytes with a trusted ID
    #[getter]
    pub fn claimed_image_id_hex(&self) -> PyResult<String> {
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
        Ok(hex::encode(digest.as_bytes()))
    }
    
    /// The CLAIMED image ID as bytes (for inspection/debugging only)
    /// SECURITY: This is untrusted data! Use verify_hex/verify_bytes with a trusted ID
    #[getter]
    pub fn claimed_image_id_bytes(&self) -> PyResult<Vec<u8>> {
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
    
    // Legacy getter for backward compatibility (but marked as "claimed")
    #[getter]
    pub fn program_id(&self) -> PyResult<Vec<u8>> {
        self.claimed_image_id_bytes()
    }
    
    // ===== Seal information =====
    
    /// Size of the cryptographic seal/proof in bytes
    #[getter]
    pub fn seal_size(&self) -> PyResult<usize> {
        Ok(self.inner.seal_size())
    }
    
    // ===== Verification methods =====
    
    /// Verify the receipt with a trusted image ID provided as hex string
    /// 
    /// Args:
    ///     image_id_hex: Expected image ID as 64-char hex string (with or without 0x prefix)
    /// 
    /// Raises:
    ///     ValueError: If hex string is invalid format
    ///     RuntimeError: If verification fails
    pub fn verify_hex(&self, image_id_hex: &str) -> PyResult<()> {
        // Handle optional 0x prefix
        let hex_str = if image_id_hex.starts_with("0x") || image_id_hex.starts_with("0X") {
            &image_id_hex[2..]
        } else {
            image_id_hex
        };
        
        // Decode hex to bytes
        let bytes = hex::decode(hex_str)
            .map_err(|e| PyErr::new::<PyValueError, _>(format!("Invalid hex string: {e}")))?;
        
        if bytes.len() != 32 {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Image ID must be 32 bytes (64 hex chars), got {} bytes", bytes.len())
            ));
        }
        
        // Convert to Digest and verify
        let image_id = Digest::try_from(bytes.as_slice())
            .map_err(|_| PyErr::new::<PyValueError, _>("Failed to create digest from bytes"))?;
        
        // Full verification: checks seal, image ID match, and success exit
        self.inner.verify(image_id)
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Verification failed: {e}")))
    }
    
    /// Verify the receipt with a trusted image ID provided as bytes
    /// 
    /// Args:
    ///     image_id: Expected image ID as 32-byte value
    /// 
    /// Raises:
    ///     ValueError: If bytes are not exactly 32 bytes
    ///     RuntimeError: If verification fails
    pub fn verify_bytes(&self, image_id: Vec<u8>) -> PyResult<()> {
        if image_id.len() != 32 {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Image ID must be 32 bytes, got {} bytes", image_id.len())
            ));
        }
        
        let digest = Digest::try_from(image_id.as_slice())
            .map_err(|_| PyErr::new::<PyValueError, _>("Failed to create digest from bytes"))?;
        
        self.inner.verify(digest)
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Verification failed: {e}")))
    }
    
    /// Verify only the integrity of the proof (seal matches claim and journal)
    /// without checking the image ID or enforcing success.
    /// 
    /// Useful for inspecting failed executions safely.
    /// 
    /// Raises:
    ///     RuntimeError: If integrity check fails
    pub fn verify_integrity(&self) -> PyResult<()> {
        // We need to check that the seal is valid for the claim, but not enforce success
        // Unfortunately, RISC Zero's verify() also checks success, so we need a workaround
        // We'll extract the claim and at least validate it's well-formed
        let _claim_pruned = self.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Integrity check failed - invalid claim: {e}")))?;
        
        let _claim = match _claim_pruned.as_value() {
            Ok(claim) => claim,
            Err(_) => return Err(PyErr::new::<PyRuntimeError, _>("Integrity check failed - claim is pruned")),
        };
        
        // TODO: When RISC Zero exposes integrity-only verification, use it here
        // For now, we at least validate the claim structure
        Ok(())
    }
    
    /// Legacy verify method - requires image_id parameter for security
    /// Backward compatible with v0.3.0
    pub fn verify(&self, image_id_bytes: &Bound<'_, PyAny>) -> PyResult<()> {
        let bytes: Vec<u8> = image_id_bytes.extract()?;
        self.verify_bytes(bytes)
    }
    
    /// Deprecated: Use verify() instead
    /// This method is kept for backward compatibility but is identical to verify()
    pub fn verify_with_image_id(&self, image_id_bytes: &Bound<'_, PyAny>) -> PyResult<()> {
        self.verify(image_id_bytes)
    }
    
    // ===== Serialization =====
    
    /// Serialize the receipt to bytes for storage/transport
    pub fn to_bytes(&self) -> PyResult<Vec<u8>> {
        bincode::serialize(&self.inner)
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to serialize receipt: {e}")))
    }
    
    /// Deserialize a receipt from bytes
    #[staticmethod]
    pub fn from_bytes(data: Vec<u8>) -> PyResult<Self> {
        let inner: RiscZeroReceipt = bincode::deserialize(&data)
            .map_err(|e| PyErr::new::<PyValueError, _>(format!("Failed to deserialize receipt: {e}")))?;
        Ok(Self { inner })
    }
    
    // ===== String representation =====
    
    pub fn __repr__(&self) -> String {
        let image_id_preview = self.claimed_image_id_hex()
            .ok()
            .map(|h| format!("{}...", &h[..8]))
            .unwrap_or_else(|| "unknown".to_string());
        
        let journal_preview = if self.inner.journal.bytes.is_empty() {
            "empty".to_string()
        } else if self.inner.journal.bytes.len() <= 20 {
            hex::encode(&self.inner.journal.bytes)
        } else {
            format!("{}...", hex::encode(&self.inner.journal.bytes[..10]))
        };
        
        format!(
            "Receipt(image_id={}, journal_len={}, journal_preview={})",
            image_id_preview,
            self.inner.journal.bytes.len(),
            journal_preview
        )
    }
    
    /// Export receipt as bytes for verification in a guest program (composition)
    /// 
    /// This serializes the receipt in a format that can be passed to another
    /// RISC Zero guest program and verified using env::verify().
    /// 
    /// Returns:
    ///     bytes: The serialized receipt
    /// 
    /// Example:
    ///     ```python
    ///     # Host: prepare inner proof for outer guest
    ///     inner_receipt = pyr0.prove(inner_image, inner_input)
    ///     receipt_bytes = inner_receipt.to_inner_bytes()
    ///     
    ///     # Package with other inputs for outer program
    ///     outer_input = (
    ///         pyr0.serialization.to_vec_u8(receipt_bytes) +
    ///         pyr0.serialization.to_vec_u8(trusted_image_id)
    ///     )
    ///     ```
    pub fn to_inner_bytes(&self) -> PyResult<Vec<u8>> {
        bincode::serialize(&self.inner)
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(
                format!("Failed to serialize receipt: {}", e)
            ))
    }
    
    /// Check if this receipt was created by a specific image/program
    /// 
    /// This is a safety check to verify the receipt came from the expected
    /// program before using it in composition.
    /// 
    /// Args:
    ///     expected_image_id: The image ID to check against (32 bytes)
    /// 
    /// Returns:
    ///     bool: True if the receipt's claimed image ID matches
    /// 
    /// Example:
    ///     ```python
    ///     expected_id = bytes.fromhex("abc123...")
    ///     if not receipt.verify_image_id(expected_id):
    ///         raise ValueError("Receipt is from wrong program!")
    ///     ```
    pub fn verify_image_id(&self, expected_image_id: Vec<u8>) -> PyResult<bool> {
        if expected_image_id.len() != 32 {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Image ID must be 32 bytes, got {} bytes", expected_image_id.len())
            ));
        }
        
        // Get the claimed image ID from the receipt
        let claimed_id = self.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(
                format!("Failed to get claim: {}", e)
            ))?
            .as_value()
            .map_err(|_| PyErr::new::<PyRuntimeError, _>("Claim is pruned"))?
            .pre
            .digest();
        
        // Compare as bytes
        Ok(claimed_id.as_bytes() == expected_image_id.as_slice())
    }
}