use anyhow::Result;
use pyo3::prelude::*;
use risc0_binfmt::{MemoryImage, Program};
use risc0_zkvm::sha::Digest;
use risc0_zkvm_platform::memory::GUEST_MAX_MEM;
use risc0_zkvm_platform::PAGE_SIZE;
use serde::{Deserialize, Serialize};

#[pyclass(module = "pyr0")]
#[derive(Serialize, Deserialize, Clone)]
pub struct Image {
    memory_image: Option<MemoryImage>,
    image_id: Option<Digest>,
    elf_bytes: Vec<u8>,
}

impl Image {
    pub fn from_elf(elf: &[u8], image_id: Digest) -> Result<Self> {
        let program = Program::load_elf(elf, GUEST_MAX_MEM as u32)?;
        let image = MemoryImage::new(&program, PAGE_SIZE as u32)?;
        Ok(Self {
            memory_image: Some(image),
            image_id: Some(image_id),
            elf_bytes: elf.to_vec(),
        })
    }

    pub fn get_image(&self) -> MemoryImage {
        self.memory_image.as_ref().unwrap().clone()
    }
    
    pub fn get_elf(&self) -> &[u8] {
        &self.elf_bytes
    }
}


#[pymethods]
impl Image {
    #[new]
    fn new_init() -> Self {
        Self { 
            memory_image: None,
            image_id: None,
            elf_bytes: Vec::new(),
        }
    }
    
    /// Return the zkVM ImageID as raw bytes (32 bytes)
    #[getter]
    pub fn id(&self) -> PyResult<Vec<u8>> {
        match &self.image_id {
            Some(id) => Ok(id.as_bytes().to_vec()),
            None => Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
                "Image has no ID (not loaded from ELF)"
            ))
        }
    }
    
    /// Return the zkVM ImageID as hex string (64 chars)
    #[getter]
    pub fn id_hex(&self) -> PyResult<String> {
        match &self.image_id {
            Some(id) => Ok(hex::encode(id.as_bytes())),
            None => Err(PyErr::new::<pyo3::exceptions::PyAttributeError, _>(
                "Image has no ID (not loaded from ELF)"
            ))
        }
    }

}
