use crate::serialization::Pickleable;
use anyhow::Result;
use pyo3::prelude::*;
use risc0_binfmt::{MemoryImage, Program};
use risc0_zkvm_platform::memory::GUEST_MAX_MEM;
use risc0_zkvm_platform::PAGE_SIZE;
use serde::{Deserialize, Serialize};

#[pyclass(module = "pyr0")]
#[derive(Serialize, Deserialize, Clone)]
pub struct Image {
    memory_image: Option<MemoryImage>,
}

impl Image {
    pub fn from_elf(elf: &[u8]) -> Result<Self> {
        let program = Program::load_elf(elf, GUEST_MAX_MEM as u32)?;
        let image = MemoryImage::new(&program, PAGE_SIZE as u32)?;
        Ok(Self {
            memory_image: Some(image),
        })
    }

    pub fn get_image(&self) -> MemoryImage {
        self.memory_image.as_ref().unwrap().clone()
    }
}

impl Pickleable for Image {}

#[pymethods]
impl Image {
    #[new]
    fn new_init() -> Self {
        Self { memory_image: None }
    }

    fn __getstate__(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.to_bytes(py)
    }

    fn __setstate__(&mut self, py: Python<'_>, state: PyObject) -> PyResult<()> {
        *self = Self::from_bytes(state, py)?;
        Ok(())
    }
}
