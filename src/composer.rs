use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError};
use risc0_zkvm::{ExecutorEnv, ProverOpts};
use risc0_zkvm::sha::{Digestible, Sha256, Digest};
use crate::image::Image;
use crate::receipt::Receipt;
use std::collections::{HashSet, HashMap};

/// A builder for composing proofs with type-safe inputs and assumptions
/// 
/// The Composer provides a safer, more ergonomic API for proof composition
/// that prevents common mistakes and aligns with RISC Zero's model.
/// 
/// Example:
///     comp = pyr0.Composer(outer_image)
///     comp.assume(inner_receipt)
///     comp.write_u32(42)
///     comp.write_bytes32(key)
///     receipt = comp.prove()
#[pyclass(module = "pyr0")]
pub struct Composer {
    image: Py<Image>,
    assumptions: Vec<risc0_zkvm::Receipt>,
    assumption_digests: HashSet<(Digest, Digest)>, // (image_id, journal_digest) for dedup
    input_data: Vec<u8>,
    expected_verifications: Vec<(Vec<u8>, Vec<u8>)>, // (image_id, journal)
}

#[pymethods]
impl Composer {
    /// Create a new Composer for the given image
    #[new]
    pub fn new(image: Py<Image>) -> Self {
        Composer {
            image,
            assumptions: Vec::new(),
            assumption_digests: HashSet::new(),
            input_data: Vec::new(),
            expected_verifications: Vec::new(),
        }
    }
    
    /// Add multiple receipts as assumptions at once
    /// 
    /// Convenience method equivalent to calling assume() for each receipt.
    /// All receipts must be unconditional (succinct/groth16) and successful.
    /// 
    /// Args:
    ///     receipts: List of unconditional receipts from successful proofs
    /// 
    /// Raises:
    ///     ValueError: If any receipt is invalid for composition
    pub fn assume_many(&mut self, receipts: Vec<PyRef<Receipt>>) -> PyResult<()> {
        for receipt in receipts {
            self.assume(&receipt)?;
        }
        Ok(())
    }
    
    /// Add a receipt as an assumption for composition
    /// 
    /// The receipt must be:
    /// - Unconditional (succinct or groth16, not composite)
    /// - Not a fake receipt (test-only)
    /// - Successfully executed (exit code 0)
    /// 
    /// Duplicate receipts (by claim digest) are automatically deduplicated.
    /// 
    /// Args:
    ///     receipt: An unconditional receipt from a successful proof
    /// 
    /// Raises:
    ///     ValueError: If receipt is invalid for composition
    pub fn assume(&mut self, receipt: &Receipt) -> PyResult<()> {
        use crate::receipt::ReceiptKind;
        
        // Check if receipt is unconditional
        if !receipt.is_unconditional()? {
            return Err(PyErr::new::<PyValueError, _>(
                "Cannot use composite receipt as assumption - it has unresolved assumptions. \
                 Use a succinct or groth16 receipt instead."
            ));
        }
        
        // Reject fake receipts
        if receipt.kind()? == ReceiptKind::Fake {
            return Err(PyErr::new::<PyValueError, _>(
                "Cannot use fake receipt as assumption - fake receipts are for testing only"
            ));
        }
        
        // Check exit status
        let exit_status = receipt.exit()?;
        if !exit_status.ok() {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Cannot use failed receipt as assumption - exit code was {}", 
                        exit_status.user_code.unwrap_or(u32::MAX))
            ));
        }
        
        // Get claim digest for deduplication
        let claim = receipt.inner.claim()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to get claim: {}", e)))?;
        let claim_value = claim.as_value()
            .map_err(|_| PyErr::new::<PyRuntimeError, _>("Claim is pruned"))?;
        
        // MaybePruned<T> implements Digestible, so we can call digest() directly
        let image_digest = claim_value.pre.digest();
        let journal_digest = *risc0_zkvm::sha::Impl::hash_bytes(&receipt.inner.journal.bytes);
        
        // Check for duplicate (dedup by claim digest)
        let claim_key = (image_digest, journal_digest);
        if self.assumption_digests.contains(&claim_key) {
            // Already added, skip to avoid duplicate resolution cost
            return Ok(());
        }
        
        // Add the assumption
        self.assumptions.push(receipt.inner.clone());
        self.assumption_digests.insert(claim_key);
        Ok(())
    }
    
    /// Write a u32 value (4 bytes, little-endian)
    /// 
    /// Guest reads with env::read_slice:
    ///     let mut bytes = [0u8; 4];
    ///     env::read_slice(&mut bytes);
    ///     let value = u32::from_le_bytes(bytes);
    pub fn write_u32(&mut self, value: u32) -> PyResult<()> {
        self.input_data.extend_from_slice(&value.to_le_bytes());
        Ok(())
    }
    
    /// Write a u64 value (8 bytes, little-endian)
    /// 
    /// Guest reads with env::read_slice:
    ///     let mut bytes = [0u8; 8];
    ///     env::read_slice(&mut bytes);
    ///     let value = u64::from_le_bytes(bytes);
    pub fn write_u64(&mut self, value: u64) -> PyResult<()> {
        self.input_data.extend_from_slice(&value.to_le_bytes());
        Ok(())
    }
    
    /// Write exactly 32 bytes (for fixed-size arrays)
    /// 
    /// Guest reads with env::read_slice:
    ///     let mut bytes = [0u8; 32];
    ///     env::read_slice(&mut bytes);
    pub fn write_bytes32(&mut self, data: Vec<u8>) -> PyResult<()> {
        if data.len() != 32 {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Expected 32 bytes, got {}", data.len())
            ));
        }
        self.input_data.extend_from_slice(&data);
        Ok(())
    }
    
    /// Write an image ID (32 bytes)
    /// 
    /// Guest reads as Digest with env::read_slice:
    ///     let mut bytes = [0u8; 32];
    ///     env::read_slice(&mut bytes);
    ///     let digest = Digest::from_bytes(bytes);
    pub fn write_image_id(&mut self, image_id: Vec<u8>) -> PyResult<()> {
        self.write_bytes32(image_id)
    }
    
    /// Write raw bytes (for env::read_slice)
    /// 
    /// Guest must know the exact length to read:
    ///     let mut buffer = [0u8; N];
    ///     env::read_slice(&mut buffer);
    pub fn write_slice(&mut self, data: Vec<u8>) -> PyResult<()> {
        self.input_data.extend_from_slice(&data);
        Ok(())
    }
    
    /// Write a Vec<u8> with length prefix (for env::read::<Vec<u8>>)
    /// 
    /// Guest reads with typed env::read:
    ///     let data: Vec<u8> = env::read::<Vec<u8>>();
    pub fn write_vec_u8(&mut self, data: Vec<u8>) -> PyResult<()> {
        // RISC Zero uses u64 little-endian for Vec length
        let len = data.len() as u64;
        self.input_data.extend_from_slice(&len.to_le_bytes());
        self.input_data.extend_from_slice(&data);
        Ok(())
    }
    
    /// Write a String with length prefix (for env::read::<String>)
    /// 
    /// Guest reads with typed env::read:
    ///     let text: String = env::read::<String>();
    pub fn write_string(&mut self, text: &str) -> PyResult<()> {
        // RISC Zero uses u64 little-endian for String length
        let bytes = text.as_bytes();
        let len = bytes.len() as u64;
        self.input_data.extend_from_slice(&len.to_le_bytes());
        self.input_data.extend_from_slice(bytes);
        Ok(())
    }
    
    /// Write the journal from a receipt
    /// 
    /// This is useful when the outer guest needs to verify the inner journal.
    pub fn write_journal_from(&mut self, receipt: &Receipt) -> PyResult<()> {
        self.input_data.extend_from_slice(&receipt.inner.journal.bytes);
        Ok(())
    }
    
    /// Register an expected env::verify() call for preflight checking
    /// 
    /// This helps catch mismatches between what the guest will verify
    /// and what assumptions were added.
    pub fn expect_verification(&mut self, image_id: Vec<u8>, journal: Vec<u8>) -> PyResult<()> {
        if image_id.len() != 32 {
            return Err(PyErr::new::<PyValueError, _>(
                format!("Image ID must be 32 bytes, got {}", image_id.len())
            ));
        }
        self.expected_verifications.push((image_id, journal));
        Ok(())
    }
    
    /// Preflight check: verify that expected verifications match assumptions
    /// 
    /// This validates that:
    /// - Each expected env::verify() has a matching assumption
    /// - Each assumption has a matching expected verification (no unused)
    /// - No duplicate expectations
    /// 
    /// Args:
    ///     raise_on_error: If True (default), raises on any mismatch
    /// 
    /// Returns:
    ///     List of issues found (empty if all checks pass)
    /// 
    /// Raises:
    ///     RuntimeError: If raise_on_error=True and issues are found
    #[pyo3(signature = (raise_on_error=true))]
    pub fn preflight_check(&self, raise_on_error: bool) -> PyResult<Vec<String>> {
        let mut issues = Vec::new();
        
        // Build map of assumption claims (for better error messages)
        let mut assumption_claims = HashMap::new();
        for assumption in &self.assumptions {
            if let Ok(claim) = assumption.claim() {
                if let Ok(claim_value) = claim.as_value() {
                    // MaybePruned<T> implements Digestible, so we can call digest() directly
                    let image_id = claim_value.pre.digest();
                    let journal_digest = *risc0_zkvm::sha::Impl::hash_bytes(&assumption.journal.bytes);
                    let key = (image_id, journal_digest);
                    *assumption_claims.entry(key).or_insert(0) += 1;
                }
            }
        }
        
        // Build map of expected verifications
        let mut expected_claims = HashMap::new();
        for (image_id, journal) in &self.expected_verifications {
            // Validate image ID is 32 bytes
            if image_id.len() != 32 {
                issues.push(format!(
                    "Invalid image ID length in expected verification: {} bytes (must be 32)",
                    image_id.len()
                ));
                continue;
            }
            
            let image_digest = risc0_zkvm::sha::Digest::try_from(image_id.as_slice())
                .map_err(|_| PyErr::new::<PyValueError, _>("Invalid image ID"))?;
            let journal_digest = *risc0_zkvm::sha::Impl::hash_bytes(journal);
            let key = (image_digest.clone(), journal_digest.clone());
            *expected_claims.entry(key).or_insert(0) += 1;
        }
        
        // Check for missing assumptions (expected but not provided)
        for ((image_id, journal_digest), count) in &expected_claims {
            match assumption_claims.get(&(*image_id, *journal_digest)) {
                None => {
                    issues.push(format!(
                        "Missing assumption for expected verification: image_id={}, journal_digest={}",
                        &hex::encode(&image_id.as_bytes()[..8]),
                        &hex::encode(&journal_digest.as_bytes()[..8])
                    ));
                }
                Some(assumption_count) if assumption_count < count => {
                    issues.push(format!(
                        "Not enough assumptions: expected {} verifications but only {} assumptions for claim",
                        count, assumption_count
                    ));
                }
                _ => {} // OK
            }
        }
        
        // Check for unused assumptions (provided but not expected)
        for ((image_id, journal_digest), _) in &assumption_claims {
            if !expected_claims.contains_key(&(*image_id, *journal_digest)) {
                issues.push(format!(
                    "Unused assumption: image_id={}, journal_digest={} (no matching env::verify expected)",
                    &hex::encode(&image_id.as_bytes()[..8]),
                    &hex::encode(&journal_digest.as_bytes()[..8])
                ));
            }
        }
        
        // Raise if requested and there are issues
        if raise_on_error && !issues.is_empty() {
            let message = format!(
                "Preflight check failed with {} issue(s):\n{}",
                issues.len(),
                issues.join("\n")
            );
            return Err(PyErr::new::<PyRuntimeError, _>(message));
        }
        
        // If not raising but there are issues, emit Python warnings
        if !issues.is_empty() && !raise_on_error {
            Python::with_gil(|py| {
                if let Ok(warnings) = py.import("warnings") {
                    for issue in &issues {
                        let _ = warnings.call_method1("warn", (issue, ));
                    }
                }
            });
        }
        
        Ok(issues)
    }
    
    /// Generate a proof with the configured assumptions and inputs
    /// 
    /// Args:
    ///     kind: ReceiptKind enum value (default: ReceiptKind.SUCCINCT)
    ///           SUCCINCT resolves assumptions via the recursion program.
    ///           COMPOSITE leaves assumptions unresolved (conditional).
    ///           GROTH16 generates final proof for on-chain verification.
    ///     preflight: If True (default), run preflight checks before proving
    /// 
    /// Returns:
    ///     Receipt: The generated proof (type depends on 'kind' parameter)
    /// 
    /// Raises:
    ///     RuntimeError: If preflight checks fail or proof generation fails
    /// 
    /// Example:
    ///     receipt = comp.prove()  # defaults to SUCCINCT
    ///     receipt = comp.prove(kind=ReceiptKind.COMPOSITE)
    #[pyo3(signature = (kind=None, preflight=true))]
    pub fn prove(&self, py: Python<'_>, kind: Option<&Bound<'_, PyAny>>, preflight: bool) -> PyResult<Receipt> {
        // Run preflight checks if requested
        if preflight {
            self.preflight_check(true)?;  // Will raise on issues
        }
        
        // Build ExecutorEnv
        let mut builder = ExecutorEnv::builder();
        
        // Add assumptions
        for assumption in &self.assumptions {
            builder.add_assumption(assumption.clone());
        }
        
        // Add input data
        if !self.input_data.is_empty() {
            builder.write_slice(&self.input_data);
        }
        
        let env = builder.build()
            .map_err(|e| PyErr::new::<PyRuntimeError, _>(format!("Failed to build environment: {}", e)))?;
        
        // Get the image
        let image = self.image.borrow(py);
        
        // Determine proof kind (default to SUCCINCT)
        use crate::receipt::ReceiptKind;
        let proof_kind = if let Some(k) = kind {
            // Try to extract ReceiptKind enum
            if let Ok(receipt_kind) = k.extract::<ReceiptKind>() {
                receipt_kind
            } else if let Ok(kind_str) = k.extract::<String>() {
                // Fallback to string for compatibility
                match kind_str.to_lowercase().as_str() {
                    "composite" => ReceiptKind::Composite,
                    "succinct" => ReceiptKind::Succinct,
                    "groth16" => ReceiptKind::Groth16,
                    _ => return Err(PyErr::new::<PyValueError, _>(
                        format!("Invalid proof kind '{}'. Use ReceiptKind.SUCCINCT, ReceiptKind.COMPOSITE, or ReceiptKind.GROTH16", kind_str)
                    )),
                }
            } else {
                return Err(PyErr::new::<PyValueError, _>(
                    "kind must be a ReceiptKind enum value or string"
                ));
            }
        } else {
            ReceiptKind::Succinct  // Default
        };
        
        // Choose prover options based on kind
        let opts = match proof_kind {
            ReceiptKind::Composite => ProverOpts::default(),
            ReceiptKind::Succinct => ProverOpts::succinct(),
            ReceiptKind::Groth16 => ProverOpts::groth16(),
            ReceiptKind::Fake => return Err(PyErr::new::<PyValueError, _>(
                "Cannot generate FAKE receipts through proving"
            )),
        };
        
        // Generate proof
        let receipt = risc0_zkvm::default_prover()
            .prove_with_opts(env, image.get_elf(), &opts)
            .map_err(|e| {
                // Try to provide better error messages for composition failures
                if e.to_string().contains("assumption") || e.to_string().contains("verify") {
                    PyErr::new::<PyRuntimeError, _>(format!(
                        "Proof generation failed - likely claim mismatch:\n{}\n\
                         Check that env::verify() calls match the assumptions provided.",
                        e
                    ))
                } else {
                    PyErr::new::<PyRuntimeError, _>(format!("Proof generation failed: {}", e))
                }
            })?
            .receipt;
        
        Ok(Receipt::from_risc0(receipt))
    }
    
    /// Get the current size of the input data buffer
    #[getter]
    pub fn input_size(&self) -> usize {
        self.input_data.len()
    }
    
    /// Get the number of assumptions added
    #[getter]
    pub fn assumption_count(&self) -> usize {
        self.assumptions.len()
    }
    
    pub fn __repr__(&self) -> String {
        format!(
            "Composer(assumptions={}, input_size={} bytes)",
            self.assumptions.len(),
            self.input_data.len()
        )
    }
}