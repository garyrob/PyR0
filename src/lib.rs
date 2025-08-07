mod image;
mod segment;
mod serialization;
mod session;
mod succinct;

use crate::image::Image;
use crate::segment::{Segment, SegmentReceipt};
use crate::session::{ExitCode, SessionInfo};
use crate::succinct::SuccinctReceipt;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use risc0_zkvm::{
    get_prover_server, ExecutorEnv, ExecutorImpl, ProverOpts, SimpleSegmentRef, VerifierContext,
};

#[pyfunction]
fn load_image_from_elf(elf: &Bound<'_, PyBytes>) -> PyResult<Image> {
    Ok(Image::from_elf(elf.as_bytes())?)
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
fn prove_segment(segment: &Segment) -> PyResult<SegmentReceipt> {
    let verifier_context = VerifierContext::default();
    let res = segment.prove(&verifier_context)?;
    Ok(res)
}

#[pyfunction]
fn lift_segment_receipt(segment_receipt: &SegmentReceipt) -> PyResult<SuccinctReceipt> {
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
fn verify_receipt(receipt: &SegmentReceipt) -> PyResult<bool> {
    receipt.verify()
}

#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Image>()?;
    m.add_class::<Segment>()?;
    m.add_class::<ExitCode>()?;
    m.add_class::<SessionInfo>()?;
    m.add_class::<SegmentReceipt>()?;
    m.add_class::<SuccinctReceipt>()?;
    m.add_function(wrap_pyfunction!(load_image_from_elf, m)?)?;
    m.add_function(wrap_pyfunction!(execute_with_input, m)?)?;
    m.add_function(wrap_pyfunction!(prove_segment, m)?)?;
    m.add_function(wrap_pyfunction!(lift_segment_receipt, m)?)?;
    m.add_function(wrap_pyfunction!(join_succinct_receipts, m)?)?;
    m.add_function(wrap_pyfunction!(join_segment_receipts, m)?)?;
    m.add_function(wrap_pyfunction!(verify_receipt, m)?)?;
    Ok(())
}
