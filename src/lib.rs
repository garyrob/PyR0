mod image;
mod receipt;
mod segment;
mod serialization;
mod session;
mod succinct;

use crate::image::Image;
use crate::receipt::Receipt;
use crate::segment::{Segment, SegmentReceipt};
use crate::session::{ExitCode, SessionInfo};
use crate::succinct::SuccinctReceipt;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use risc0_zkvm::{
    get_prover_server, ExecutorEnv, ExecutorImpl, ProverOpts, SimpleSegmentRef,
};

#[pyfunction]
fn load_image(elf: &Bound<'_, PyBytes>) -> PyResult<Image> {
    let elf_bytes = elf.as_bytes();
    // Compute the image ID from the ELF
    let image_id = risc0_binfmt::compute_image_id(elf_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to compute image ID: {}", e)))?;
    
    Ok(Image::from_elf(elf_bytes, image_id)?)
}

#[pyfunction]
#[pyo3(signature = (image, input, segment_size_limit=None))]
fn execute_with_input(
    image: &Image,
    input: &Bound<'_, PyBytes>,
    segment_size_limit: Option<u32>,
) -> PyResult<(Vec<Segment>, SessionInfo)> {
    let mut env_builder = ExecutorEnv::builder();
    env_builder.write_slice(input.as_bytes());

    if let Some(segment_size_limit) = segment_size_limit {
        env_builder.segment_limit_po2(segment_size_limit);
    }
    let env = env_builder.build()?;

    let mut exec = ExecutorImpl::new(env, image.get_image())?;

    let session = exec.run_with_callback(|segment| Ok(Box::new(SimpleSegmentRef::new(segment))))?;

    let mut segments = vec![];
    for segment_ref in session.segments.iter() {
        segments.push(Segment::new(segment_ref.resolve()?));
    }

    let session_info = SessionInfo::new(&session)?;
    Ok((segments, session_info))
}

#[pyfunction]
fn generate_proof(segment: &Segment) -> PyResult<SegmentReceipt> {
    let verifier_context = risc0_zkvm::VerifierContext::default();
    let res = segment.prove(&verifier_context)?;
    Ok(res)
}

#[pyfunction]
fn lift_receipt(segment_receipt: &SegmentReceipt) -> PyResult<SuccinctReceipt> {
    let prover = get_prover_server(&ProverOpts::default())?;
    Ok(SuccinctReceipt::new(
        prover.lift(segment_receipt.get_segment_receipt_ref())?,
    ))
}

#[pyfunction]
fn join_succinct_receipts(receipts: Vec<PyRef<SuccinctReceipt>>) -> PyResult<SuccinctReceipt> {
    let prover = get_prover_server(&ProverOpts::default())?;
    assert!(receipts.len() > 0);

    if receipts.len() == 1 {
        Ok(receipts[0].clone())
    } else {
        let mut acc = prover.join(
            receipts[0].get_succinct_receipt_ref(),
            receipts[1].get_succinct_receipt_ref(),
        )?;
        for receipt in receipts.iter().skip(2) {
            acc = prover.join(&acc, &receipt.get_succinct_receipt_ref())?;
        }
        Ok(SuccinctReceipt::new(acc))
    }
}

#[pyfunction]
fn join_segment_receipts(receipts: Vec<PyRef<SegmentReceipt>>) -> PyResult<SuccinctReceipt> {
    let prover = get_prover_server(&ProverOpts::default())?;
    assert!(receipts.len() > 0);

    if receipts.len() == 1 {
        Ok(SuccinctReceipt::new(
            prover.lift(receipts[0].get_segment_receipt_ref())?,
        ))
    } else {
        let mut acc = prover.lift(receipts[0].get_segment_receipt_ref())?;
        for receipt in receipts.iter().skip(1) {
            acc = prover.join(&acc, &prover.lift(receipt.get_segment_receipt_ref())?)?;
        }
        Ok(SuccinctReceipt::new(acc))
    }
}

#[pyfunction]
#[pyo3(signature = (receipt))]
fn verify_proof(receipt: &SegmentReceipt) -> PyResult<()> {
    receipt.verify_integrity()
}

/// Prepare input data for passing to guest - simple pass-through of bytes
/// The Python side is responsible for proper serialization
#[pyfunction]
fn prepare_input<'py>(py: Python<'py>, data: &[u8]) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
    Ok(pyo3::types::PyBytes::new(py, data))
}


#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Image>()?;
    m.add_class::<Segment>()?;
    m.add_class::<ExitCode>()?;
    m.add_class::<SessionInfo>()?;
    m.add_class::<Receipt>()?;
    m.add_class::<SegmentReceipt>()?;
    m.add_class::<SuccinctReceipt>()?;
    
    // API functions
    m.add_function(wrap_pyfunction!(load_image, m)?)?;
    m.add_function(wrap_pyfunction!(execute_with_input, m)?)?;
    m.add_function(wrap_pyfunction!(generate_proof, m)?)?;
    m.add_function(wrap_pyfunction!(lift_receipt, m)?)?;
    m.add_function(wrap_pyfunction!(join_succinct_receipts, m)?)?;
    m.add_function(wrap_pyfunction!(join_segment_receipts, m)?)?;
    m.add_function(wrap_pyfunction!(verify_proof, m)?)?;
    m.add_function(wrap_pyfunction!(prepare_input, m)?)?;
    Ok(())
}
