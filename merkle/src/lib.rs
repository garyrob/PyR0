mod merkle;

use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};
use pyo3::exceptions::PyValueError;
use std::sync::{Arc, RwLock};

use crate::merkle::{CommitmentSet, hex_to_h256, h256_to_hex};

/// Python wrapper for the sparse Merkle tree
#[pyclass]
struct MerkleTree {
    inner: Arc<RwLock<CommitmentSet>>,
}

#[pymethods]
impl MerkleTree {
    /// Create a new empty Merkle tree
    #[new]
    fn new() -> Self {
        MerkleTree {
            inner: Arc::new(RwLock::new(CommitmentSet::new())),
        }
    }
    
    /// Insert a key into the tree (as hex string or bytes)
    fn insert(&self, key: &Bound<'_, PyAny>) -> PyResult<()> {
        let key_str = if let Ok(bytes) = key.downcast::<PyBytes>() {
            hex::encode(bytes.as_bytes())
        } else if let Ok(s) = key.extract::<String>() {
            s
        } else {
            return Err(PyValueError::new_err("Key must be bytes or string"));
        };
        
        let h256_key = hex_to_h256(&key_str)
            .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
        
        let mut tree = self.inner.write().unwrap();
        tree.insert(h256_key);
        Ok(())
    }
    
    /// Check if a key exists in the tree
    fn contains(&self, key: &Bound<'_, PyAny>) -> PyResult<bool> {
        let key_str = if let Ok(bytes) = key.downcast::<PyBytes>() {
            hex::encode(bytes.as_bytes())
        } else if let Ok(s) = key.extract::<String>() {
            s
        } else {
            return Err(PyValueError::new_err("Key must be bytes or string"));
        };
        
        let h256_key = hex_to_h256(&key_str)
            .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
        
        let tree = self.inner.read().unwrap();
        Ok(tree.contains(&h256_key))
    }
    
    /// Get the current root of the tree as hex string
    fn root(&self) -> String {
        let tree = self.inner.read().unwrap();
        h256_to_hex(&tree.root())
    }
    
    /// Get the current root of the tree as bytes
    fn root_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        let tree = self.inner.read().unwrap();
        let root = tree.root();
        let bytes: [u8; 32] = root.into();
        PyBytes::new(py, &bytes)
    }
    
    /// Generate a Merkle path (16 levels) for a given key
    /// Returns a tuple of (siblings, index_bits)
    fn merkle_path_16<'py>(&self, py: Python<'py>, key: &Bound<'_, PyAny>) -> PyResult<(Bound<'py, PyList>, Bound<'py, PyList>)> {
        let key_str = if let Ok(bytes) = key.downcast::<PyBytes>() {
            hex::encode(bytes.as_bytes())
        } else if let Ok(s) = key.extract::<String>() {
            s
        } else {
            return Err(PyValueError::new_err("Key must be bytes or string"));
        };
        
        let h256_key = hex_to_h256(&key_str)
            .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
        
        let tree = self.inner.read().unwrap();
        let (siblings, bits) = tree.merkle_path_16(&h256_key);
        
        let siblings_list = PyList::new(py, siblings)?;
        let bits_list = PyList::new(py, bits)?;
        
        Ok((siblings_list, bits_list))
    }
    
    /// Generate a full Merkle proof for a given key
    /// Returns a dict with proof data
    fn merkle_proof<'py>(&self, py: Python<'py>, key: &Bound<'_, PyAny>) -> PyResult<Bound<'py, PyDict>> {
        let key_str = if let Ok(bytes) = key.downcast::<PyBytes>() {
            hex::encode(bytes.as_bytes())
        } else if let Ok(s) = key.extract::<String>() {
            s
        } else {
            return Err(PyValueError::new_err("Key must be bytes or string"));
        };
        
        let h256_key = hex_to_h256(&key_str)
            .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
        
        let tree = self.inner.read().unwrap();
        let proof = tree.merkle_proof(&h256_key)
            .map_err(|e| PyValueError::new_err(format!("Failed to generate proof: {:?}", e)))?;
        
        let (bitmaps, siblings) = proof.take();
        
        let result = PyDict::new(py);
        
        // Convert bitmaps to list of hex strings
        let bitmap_list = PyList::empty(py);
        for bitmap in bitmaps {
            let bytes: [u8; 32] = bitmap.into();
            bitmap_list.append(hex::encode(bytes))?;
        }
        result.set_item("bitmaps", bitmap_list)?;
        
        // Convert siblings to list of hex strings
        let sibling_list = PyList::empty(py);
        for sibling in siblings {
            let hash = sibling.hash::<merkle::PoseidonHasher>();
            let bytes: [u8; 32] = hash.into();
            sibling_list.append(hex::encode(bytes))?;
        }
        result.set_item("siblings", sibling_list)?;
        
        Ok(result)
    }
    
    
    /// Batch insert multiple keys
    fn batch_insert(&self, keys: &Bound<'_, PyList>) -> PyResult<()> {
        let mut tree = self.inner.write().unwrap();
        
        for key in keys.iter() {
            let key_str = if let Ok(bytes) = key.downcast::<PyBytes>() {
                hex::encode(bytes.as_bytes())
            } else if let Ok(s) = key.extract::<String>() {
                s
            } else {
                return Err(PyValueError::new_err("All keys must be bytes or strings"));
            };
            
            let h256_key = hex_to_h256(&key_str)
                .map_err(|e| PyValueError::new_err(format!("Invalid key: {}", e)))?;
            
            tree.insert(h256_key);
        }
        
        Ok(())
    }
}

/// Utility function to compute Poseidon hash of inputs
#[pyfunction]
fn poseidon_hash<'py>(py: Python<'py>, inputs: &Bound<'_, PyList>) -> PyResult<Bound<'py, PyBytes>> {
    use num_bigint::BigUint;
    use poseidon_bn128::poseidon;
    use scalarff::{Bn128FieldElement, FieldElement};
    
    let mut field_elements = Vec::new();
    
    for input in inputs.iter() {
        let bytes = if let Ok(bytes) = input.downcast::<PyBytes>() {
            bytes.as_bytes().to_vec()
        } else if let Ok(s) = input.extract::<String>() {
            let clean = s.trim_start_matches("0x");
            hex::decode(clean)
                .map_err(|e| PyValueError::new_err(format!("Invalid hex: {}", e)))?
        } else {
            return Err(PyValueError::new_err("Inputs must be bytes or hex strings"));
        };
        
        let n = BigUint::from_bytes_be(&bytes);
        let fe = Bn128FieldElement::from_biguint(&n);
        field_elements.push(fe);
    }
    
    let result = poseidon(field_elements.len() as u8, &field_elements)
        .map_err(|e| PyValueError::new_err(format!("Poseidon hash failed: {:?}", e)))?;
    
    let mut bytes = result.to_biguint().to_bytes_be();
    if bytes.len() < 32 {
        let mut padded = vec![0u8; 32 - bytes.len()];
        padded.append(&mut bytes);
        bytes = padded;
    } else if bytes.len() > 32 {
        bytes = bytes[bytes.len() - 32..].to_vec();
    }
    
    Ok(PyBytes::new(py, &bytes))
}

/// Convert hex string to 32-byte array (H256)
#[pyfunction]
fn hex_to_bytes<'py>(py: Python<'py>, hex_str: &str) -> PyResult<Bound<'py, PyBytes>> {
    let h256 = hex_to_h256(hex_str)
        .map_err(|e| PyValueError::new_err(format!("Invalid hex: {}", e)))?;
    let bytes: [u8; 32] = h256.into();
    Ok(PyBytes::new(py, &bytes))
}

/// Convert bytes to hex string
#[pyfunction]
fn bytes_to_hex(data: &Bound<'_, PyBytes>) -> PyResult<String> {
    Ok(hex::encode(data.as_bytes()))
}

/// Python module initialization
#[pymodule]
fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MerkleTree>()?;
    m.add_function(wrap_pyfunction!(poseidon_hash, m)?)?;
    m.add_function(wrap_pyfunction!(hex_to_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(bytes_to_hex, m)?)?;
    Ok(())
}