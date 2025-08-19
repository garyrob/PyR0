mod image;
mod receipt;
mod session;
mod executor_env;

use crate::image::Image;
use crate::receipt::{Receipt, ExitStatus, ExitKind};
use crate::session::{ExitCode, SessionInfo};
use crate::executor_env::PyExecutorEnv;
use pyo3::prelude::*;
use risc0_zkvm::{default_prover, ExecutorEnv, ProverOpts};

#[pyfunction]
fn load_image(elf: &Bound<'_, PyAny>) -> PyResult<Image> {
    let elf_bytes: Vec<u8> = elf.extract()?;
    // Compute the image ID from the ELF
    let image_id = risc0_binfmt::compute_image_id(&elf_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to compute image ID: {}", e)))?;
    
    Ok(Image::from_elf(&elf_bytes, image_id)?)
}

// For testing/debugging - execute without proving
#[pyfunction]
#[pyo3(signature = (image, input_bytes))]
fn dry_run(
    _py: Python<'_>,
    image: &Image,
    input_bytes: &Bound<'_, PyAny>,
) -> PyResult<SessionInfo> {
    // Accept any bytes-like object and convert to bytes
    let bytes: Vec<u8> = input_bytes.extract()?;
    
    let env = ExecutorEnv::builder()
        .write_slice(&bytes)
        .build()?;

    let mut exec = risc0_zkvm::ExecutorImpl::new(env, image.get_image())?;
    let session = exec.run()?;
    
    Ok(SessionInfo::new(&session)?)
}


/// Unified function to execute and prove in one call
#[pyfunction]
#[pyo3(signature = (image, input_bytes))]
fn prove(_py: Python<'_>, image: &Image, input_bytes: &Bound<'_, PyAny>) -> PyResult<Receipt> {
    // Accept any bytes-like object and convert to bytes
    let bytes: Vec<u8> = input_bytes.extract()?;
    
    // Build the execution environment
    let env = ExecutorEnv::builder()
        .write_slice(&bytes)
        .build()?;
    
    // Use RISC Zero's high-level API - no segment handling needed!
    let receipt = default_prover()
        .prove(env, image.get_elf())?
        .receipt;
    
    // Return a Receipt that wraps the RISC Zero receipt
    Ok(Receipt::from_risc0(receipt))
}

/// Execute and prove with specific options (e.g., succinct, groth16)
#[pyfunction]
#[pyo3(signature = (image, input_bytes, succinct=false))]
fn prove_with_opts(_py: Python<'_>, image: &Image, input_bytes: &Bound<'_, PyAny>, succinct: bool) -> PyResult<Receipt> {
    let bytes: Vec<u8> = input_bytes.extract()?;
    
    let env = ExecutorEnv::builder()
        .write_slice(&bytes)
        .build()?;
    
    let opts = if succinct {
        ProverOpts::succinct()
    } else {
        ProverOpts::default()
    };
    
    let receipt = default_prover()
        .prove_with_opts(env, image.get_elf(), &opts)?
        .receipt;
    
    Ok(Receipt::from_risc0(receipt))
}

/// Execute and prove with a custom ExecutorEnv (for composition)
/// 
/// This allows proof composition by adding assumptions.
/// 
/// Args:
///     image: The Image containing the RISC-V ELF
///     env: ExecutorEnv with assumptions and input data
/// 
/// Returns:
///     Receipt proving execution with all assumptions
#[pyfunction]
fn prove_with_env(_py: Python<'_>, image: &Image, env: &PyExecutorEnv) -> PyResult<Receipt> {
    let executor_env = env.build_env()?;
    
    // Use default prover with the custom environment
    let receipt = default_prover()
        .prove(executor_env, image.get_elf())?
        .receipt;
    
    Ok(Receipt::from_risc0(receipt))
}

// Advanced functions removed - segments are no longer exposed
// If needed in future, these could work with Receipt types instead

/// Compute the expected image ID from an ELF file as hex string
/// 
/// Args:
///     elf_bytes: The ELF binary to compute ID from
/// 
/// Returns:
///     64-character hex string of the image ID
#[pyfunction]
fn compute_image_id_hex(elf_bytes: Vec<u8>) -> PyResult<String> {
    let image_id = risc0_binfmt::compute_image_id(&elf_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to compute image ID: {}", e)
        ))?;
    Ok(hex::encode(image_id))
}




#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Image>()?;
    m.add_class::<ExitCode>()?;
    m.add_class::<SessionInfo>()?;
    m.add_class::<Receipt>()?;
    m.add_class::<ExitStatus>()?;
    m.add_class::<ExitKind>()?;
    m.add_class::<PyExecutorEnv>()?;
    
    // Core API functions
    m.add_function(wrap_pyfunction!(load_image, m)?)?;
    m.add_function(wrap_pyfunction!(prove, m)?)?;
    m.add_function(wrap_pyfunction!(prove_with_opts, m)?)?;
    m.add_function(wrap_pyfunction!(prove_with_env, m)?)?;
    m.add_function(wrap_pyfunction!(compute_image_id_hex, m)?)?;
    
    // Optional debugging function
    m.add_function(wrap_pyfunction!(dry_run, m)?)?;
    
    Ok(())
}
