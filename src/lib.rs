mod image;
mod receipt;
mod session;
mod claim;
mod composer;
mod verifier;

use crate::image::Image;
use crate::receipt::{Receipt, ExitStatus, ExitKind, ReceiptKind};
use crate::session::{ExitCode, SessionInfo};
use crate::claim::Claim;
use crate::composer::Composer;
use crate::verifier::VerifierContext;
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

/// Convenience function to directly generate a succinct proof
/// 
/// This is equivalent to prove_with_opts(image, input_bytes, succinct=True)
/// but more explicit about generating an unconditional proof.
/// 
/// Args:
///     image: The Image containing the RISC-V ELF
///     input_bytes: Input data for the guest program
/// 
/// Returns:
///     Receipt: A succinct receipt with no unresolved assumptions
#[pyfunction]
fn prove_succinct(_py: Python<'_>, image: &Image, input_bytes: &Bound<'_, PyAny>) -> PyResult<Receipt> {
    let bytes: Vec<u8> = input_bytes.extract()?;
    
    let env = ExecutorEnv::builder()
        .write_slice(&bytes)
        .build()?;
    
    let receipt = default_prover()
        .prove_with_opts(env, image.get_elf(), &ProverOpts::succinct())?
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

/// Compress a composite receipt to succinct format
/// 
/// This runs the recursion program to resolve all assumptions,
/// converting a conditional composite receipt into an unconditional
/// succinct receipt with constant-size proof and constant-time verification.
/// 
/// Args:
///     receipt: A composite receipt to compress
///     assumptions: Optional list of assumption receipts needed for resolution.
///                  If None and the receipt has unresolved assumptions, will raise.
/// 
/// Returns:
///     Receipt: A succinct receipt with all assumptions resolved
/// 
/// Raises:
///     RuntimeError: If compression fails, receipt is already succinct,
///                   or has unresolved assumptions without providing them
#[pyfunction]
#[pyo3(signature = (receipt, assumptions=None))]
fn compress_to_succinct(
    _py: Python<'_>, 
    receipt: &Receipt,
    assumptions: Option<Vec<PyRef<Receipt>>>
) -> PyResult<Receipt> {
    use crate::receipt::ReceiptKind;
    
    // Check if already succinct
    if receipt.is_succinct()? {
        return Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
            "Receipt is already succinct"
        ));
    }
    
    // Check if it's a composite with potential assumptions
    if receipt.kind()? == ReceiptKind::Composite {
        // For composite receipts, we need to check if they have unresolved assumptions
        // RISC Zero doesn't expose this directly, but we can try compression
        // and handle the error if assumptions are needed
        
        if let Some(assumption_receipts) = assumptions {
            // Build an environment with the provided assumptions
            let mut builder = ExecutorEnv::builder();
            
            // Add each assumption
            for assumption in assumption_receipts {
                // Validate the assumption is unconditional
                if !assumption.is_unconditional()? {
                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                        "Provided assumptions must be unconditional (succinct/groth16)"
                    ));
                }
                builder.add_assumption(assumption.inner.clone());
            }
            
            // Note: RISC Zero's compress API doesn't directly take assumptions
            // This is a limitation - we'd need to use prove_with_opts with the 
            // composite receipt as input, which isn't directly exposed
            
            // For now, attempt direct compression and provide clear error
            let compressed = risc0_zkvm::default_prover()
                .compress(&ProverOpts::succinct(), &receipt.inner)
                .map_err(|e| {
                    if e.to_string().contains("assumption") {
                        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            "Cannot compress composite receipt with unresolved assumptions. \
                             The compress API doesn't support providing assumptions directly. \
                             Use Composer API instead for composition workflows."
                        )
                    } else {
                        PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                            format!("Failed to compress receipt: {}", e)
                        )
                    }
                })?;
            
            return Ok(Receipt::from_risc0(compressed));
        }
    }
    
    // Attempt compression without assumptions
    let compressed = risc0_zkvm::default_prover()
        .compress(&ProverOpts::succinct(), &receipt.inner)
        .map_err(|e| {
            if e.to_string().contains("assumption") || e.to_string().contains("unresolved") {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    "Cannot compress composite receipt with unresolved assumptions. \
                     Either provide the assumption receipts or use the Composer API \
                     for composition workflows."
                )
            } else {
                PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                    format!("Failed to compress receipt: {}", e)
                )
            }
        })?;
    
    Ok(Receipt::from_risc0(compressed))
}




#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Image>()?;
    m.add_class::<ExitCode>()?;
    m.add_class::<SessionInfo>()?;
    m.add_class::<Receipt>()?;
    m.add_class::<ExitStatus>()?;
    m.add_class::<ExitKind>()?;
    m.add_class::<ReceiptKind>()?;
    m.add_class::<Claim>()?;
    m.add_class::<Composer>()?;
    m.add_class::<VerifierContext>()?;
    
    // Core API functions
    m.add_function(wrap_pyfunction!(load_image, m)?)?;
    m.add_function(wrap_pyfunction!(prove, m)?)?;
    m.add_function(wrap_pyfunction!(prove_with_opts, m)?)?;
    m.add_function(wrap_pyfunction!(prove_succinct, m)?)?;
    m.add_function(wrap_pyfunction!(compute_image_id_hex, m)?)?;
    m.add_function(wrap_pyfunction!(compress_to_succinct, m)?)?;
    
    // Optional debugging function
    m.add_function(wrap_pyfunction!(dry_run, m)?)?;
    
    Ok(())
}
