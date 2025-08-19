use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use risc0_zkvm::ExecutorEnv as RiscExecutorEnv;
use crate::receipt::Receipt as PyReceipt;

/// Python wrapper for RISC Zero's ExecutorEnv builder
/// 
/// This allows building execution environments with assumptions for proof composition.
/// 
/// Example:
///     env = pyr0.ExecutorEnv()
///     env.add_assumption(inner_receipt)
///     env.write(input_data)
///     receipt = pyr0.prove_with_env(image, env)
#[pyclass(name = "ExecutorEnv", module = "pyr0")]
pub struct PyExecutorEnv {
    assumptions: Vec<risc0_zkvm::Receipt>,
    input_data: Vec<u8>,
}

#[pymethods]
impl PyExecutorEnv {
    /// Create a new ExecutorEnv builder
    #[new]
    pub fn new() -> Self {
        PyExecutorEnv {
            assumptions: Vec::new(),
            input_data: Vec::new(),
        }
    }
    
    /// Add a receipt as an assumption for composition
    /// 
    /// The receipt will be verified when the final proof is generated.
    /// This enables efficient proof composition using RISC Zero's recursion.
    /// 
    /// Args:
    ///     receipt: A receipt from a previous proof
    /// 
    /// Returns:
    ///     self: For method chaining
    pub fn add_assumption(&mut self, receipt: &PyReceipt) -> PyResult<()> {
        self.assumptions.push(receipt.inner.clone());
        Ok(())
    }
    
    /// Write input data to the environment
    /// 
    /// Args:
    ///     data: Bytes to write as input
    /// 
    /// Returns:
    ///     self: For method chaining
    pub fn write(&mut self, data: Vec<u8>) -> PyResult<()> {
        self.input_data.extend_from_slice(&data);
        Ok(())
    }
}

impl PyExecutorEnv {
    /// Build the ExecutorEnv (internal use - not exposed to Python)
    pub fn build_env(&self) -> PyResult<RiscExecutorEnv<'static>> {
        let mut builder = RiscExecutorEnv::builder();
        
        // Add all assumptions
        for assumption in &self.assumptions {
            builder.add_assumption(assumption.clone());
        }
        
        // Add input data
        if !self.input_data.is_empty() {
            builder.write_slice(&self.input_data);
        }
        
        Ok(builder.build()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(
                format!("Failed to build ExecutorEnv: {}", e)
            ))?)
    }
}