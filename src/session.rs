use crate::serialization::Pickleable;
use anyhow::Result;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[pyclass(module = "pyr0")]
#[derive(Clone, Serialize, Deserialize)]
pub struct ExitCode {
    exit_code: Option<risc0_zkvm::ExitCode>,
}

impl ExitCode {
    pub fn new(exit_code: risc0_zkvm::ExitCode) -> Self {
        Self {
            exit_code: Some(exit_code),
        }
    }
}

impl Pickleable for ExitCode {}

#[pymethods]
impl ExitCode {
    pub fn is_system_split(&self) -> PyResult<bool> {
        Ok(matches!(
            self.exit_code,
            Some(risc0_zkvm::ExitCode::SystemSplit)
        ))
    }

    pub fn is_session_limit(&self) -> PyResult<bool> {
        Ok(matches!(
            self.exit_code,
            Some(risc0_zkvm::ExitCode::SessionLimit)
        ))
    }

    pub fn is_paused(&self) -> PyResult<bool> {
        Ok(matches!(
            self.exit_code,
            Some(risc0_zkvm::ExitCode::Paused(_))
        ))
    }

    pub fn get_paused_code(&self) -> PyResult<u32> {
        match self.exit_code {
            Some(risc0_zkvm::ExitCode::Paused(v)) => Ok(v),
            _ => Err(PyValueError::new_err("The exit code is not for pausing.")),
        }
    }

    pub fn is_halted(&self) -> PyResult<bool> {
        Ok(matches!(
            self.exit_code,
            Some(risc0_zkvm::ExitCode::Halted(_))
        ))
    }

    pub fn get_halted_code(&self) -> PyResult<u32> {
        match self.exit_code {
            Some(risc0_zkvm::ExitCode::Halted(v)) => Ok(v),
            _ => Err(PyValueError::new_err("The exit code is not for halting.")),
        }
    }

    pub fn is_fault(&self) -> PyResult<bool> {
        // In RISC Zero 1.2, there's no Fault variant, only SystemSplit
        Ok(matches!(self.exit_code, Some(risc0_zkvm::ExitCode::SystemSplit)))
    }

    #[new]
    fn new_init() -> Self {
        Self { exit_code: None }
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
pub struct SessionInfo {
    journal: Option<Vec<u8>>,
    exit_code: ExitCode,
}

impl SessionInfo {
    pub fn new(session: &risc0_zkvm::Session) -> Result<Self> {
        let journal = match &session.journal {
            Some(v) => v.bytes.clone(),
            None => vec![],
        };
        Ok(Self {
            journal: Some(journal),
            exit_code: ExitCode::new(session.exit_code),
        })
    }
}

impl Pickleable for SessionInfo {}

#[pymethods]
impl SessionInfo {
    #[new]
    fn new_init() -> Self {
        Self {
            journal: None,
            exit_code: ExitCode::new_init(),
        }
    }

    pub fn get_journal(&self) -> PyResult<Vec<u8>> {
        Ok(self.journal.as_ref().unwrap().clone())
    }

    pub fn get_exit_code(&self) -> PyResult<ExitCode> {
        Ok(self.exit_code.clone())
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.to_bytes(py)
    }

    fn __setstate__(&mut self, py: Python<'_>, state: PyObject) -> PyResult<()> {
        *self = Self::from_bytes(state, py)?;
        Ok(())
    }
}
