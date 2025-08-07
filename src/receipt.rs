use pyo3::prelude::*;
use pyo3::types::PyBytes;
use risc0_zkvm::Receipt as R0Receipt;

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
        let id_bytes = self.inner.claim.as_value().unwrap().pre.digest().as_bytes();
        Ok(PyBytes::new(py, id_bytes))
    }
    
    /// Get a string representation for debugging
    pub fn __repr__(&self) -> String {
        format!("Receipt(journal_len={}, proven=true)", self.inner.journal.bytes.len())
    }
}