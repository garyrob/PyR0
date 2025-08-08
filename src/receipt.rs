use pyo3::prelude::*;
use pyo3::types::PyBytes;
use risc0_zkvm::Receipt as R0Receipt;
use risc0_zkvm::sha::Digestible;

/// A zero-knowledge proof receipt that can be shared and verified
#[pyclass]
#[derive(Clone)]
pub struct Receipt {
    pub(crate) inner: R0Receipt,
}

#[pymethods]
impl Receipt {
    /// Serialize receipt to bytes for storage/transmission
    pub fn to_bytes<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        let bytes = bincode::serialize(&self.inner)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to serialize receipt: {}", e)
            ))?;
        Ok(PyBytes::new(py, &bytes))
    }
    
    /// Create receipt from bytes
    #[staticmethod]
    pub fn from_bytes(data: &[u8]) -> PyResult<Self> {
        let inner = bincode::deserialize(data)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Failed to deserialize receipt: {}", e)
            ))?;
        Ok(Receipt { inner })
    }
    
    /// Get the journal (public outputs) as bytes
    pub fn journal_bytes<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        Ok(PyBytes::new(py, &self.inner.journal.bytes))
    }
    
    /// Get the program ID that was executed
    pub fn program_id<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyBytes>> {
        // The program ID is the image_id from the claim
        let claim = self.inner.claim()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Failed to get claim: {}", e)
            ))?;
        let claim_value = claim.as_value()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Claim value is pruned: {}", e)
            ))?;
        let digest = claim_value.pre.digest();
        let id_bytes = digest.as_bytes();
        Ok(PyBytes::new(py, id_bytes))
    }
    
    /// Get a string representation for debugging
    pub fn __repr__(&self) -> String {
        format!("Receipt(journal_len={}, proven=true)", self.inner.journal.bytes.len())
    }
    
    /// Verify the receipt with the given image ID.
    /// This performs full verification including:
    /// - Cryptographic verification of the seal
    /// - Checking that the guest exited successfully
    /// - Verifying the image ID matches the expected value
    /// - Ensuring the journal has not been tampered with
    pub fn verify(&self, image_id_hex: &str) -> PyResult<()> {
        // Parse hex string to bytes
        let hex_bytes = hex::decode(image_id_hex)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Invalid image ID hex string: {}", e)
            ))?;
        
        // Convert to fixed-size array
        let mut bytes = [0u8; 32];
        if hex_bytes.len() != 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Image ID must be exactly 32 bytes (64 hex characters)"
            ));
        }
        bytes.copy_from_slice(&hex_bytes);
        
        let image_id = risc0_zkvm::sha::Digest::from_bytes(bytes);
            
        self.inner.verify(image_id)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                format!("Verification failed: {}", e)
            ))
    }
}