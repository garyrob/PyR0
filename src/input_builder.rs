use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

/// A builder for constructing input data for RISC Zero guests
/// 
/// This provides a simplified, consistent API for serializing data to pass to guests.
/// Choose ONE pattern per guest:
/// 
/// 1. **CBOR-only**: Single CBOR object containing all data
/// 2. **Raw-only**: Fixed-size fields read with env::read_slice()
/// 3. **Framed**: Mix CBOR and raw with explicit length prefixes
/// 
/// Example:
///     import cbor2
///     builder = pyr0.InputBuilder()
///     builder.write_cbor(cbor2.dumps({"key": "value"}))
///     builder.write_u32(42)
///     input_data = builder.build()
///     receipt = pyr0.prove(image, input_data)
#[pyclass(module = "pyr0")]
pub struct InputBuilder {
    data: Vec<u8>,
}

#[pymethods]
impl InputBuilder {
    /// Create a new InputBuilder
    #[new]
    pub fn new() -> Self {
        Self {
            data: Vec::new(),
        }
    }
    
    /// Write CBOR-encoded data WITHOUT length prefix (Pattern A: CBOR-only)
    /// 
    /// ⚠️ Use this ONLY if your entire input is a single CBOR object.
    /// Do NOT mix with write_u32/write_raw_bytes unless using write_cbor_frame.
    /// 
    /// **Python code:**
    /// ```python
    /// import cbor2
    /// data = {"field1": 123, "field2": b"hello"}
    /// builder.write_cbor(cbor2.dumps(data, canonical=True))
    /// ```
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut buf = Vec::new();
    /// env::stdin().read_to_end(&mut buf).unwrap();
    /// let input: Input = minicbor::decode(&buf).unwrap();  // Entire buffer is CBOR
    /// ```
    pub fn write_cbor(mut slf: PyRefMut<Self>, cbor_bytes: Vec<u8>) -> PyRefMut<Self> {
        slf.data.extend_from_slice(&cbor_bytes);
        slf
    }
    
    /// Write a u32 value (4 bytes, little-endian) for Pattern B: Raw-only
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut bytes = [0u8; 4];
    /// env::read_slice(&mut bytes);
    /// let value = u32::from_le_bytes(bytes);
    /// ```
    pub fn write_u32(mut slf: PyRefMut<Self>, value: u32) -> PyRefMut<Self> {
        slf.data.extend_from_slice(&value.to_le_bytes());
        slf
    }
    
    /// Write a u64 value (8 bytes, little-endian) for Pattern B: Raw-only
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut bytes = [0u8; 8];
    /// env::read_slice(&mut bytes);
    /// let value = u64::from_le_bytes(bytes);
    /// ```
    pub fn write_u64(mut slf: PyRefMut<Self>, value: u64) -> PyRefMut<Self> {
        slf.data.extend_from_slice(&value.to_le_bytes());
        slf
    }
    
    /// Write exactly 32 bytes (enforces length)
    /// 
    /// Common for cryptographic keys, hashes, and image IDs.
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut bytes = [0u8; 32];
    /// env::read_slice(&mut bytes);
    /// ```
    pub fn write_bytes32(mut slf: PyRefMut<Self>, data: Vec<u8>) -> PyResult<PyRefMut<Self>> {
        if data.len() != 32 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("write_bytes32 requires exactly 32 bytes, got {}", data.len())
            ));
        }
        slf.data.extend_from_slice(&data);
        Ok(slf)
    }
    
    /// Write an image ID (alias for write_bytes32)
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut image_id = [0u8; 32];
    /// env::read_slice(&mut image_id);
    /// ```
    pub fn write_image_id(slf: PyRefMut<Self>, image_id: Vec<u8>) -> PyResult<PyRefMut<Self>> {
        Self::write_bytes32(slf, image_id)
    }
    
    /// Write raw bytes without any encoding (ADVANCED)
    /// 
    /// ⚠️ Use this only when you need exact control over the byte layout.
    /// The guest must know the exact number of bytes to read.
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut buffer = [0u8; N];  // Must know N at compile time!
    /// env::read_slice(&mut buffer);
    /// ```
    /// 
    /// For variable-length data, use write_frame() or write_cbor_frame().
    /// 
    /// Returns self for method chaining.
    pub fn write_raw_bytes(mut slf: PyRefMut<Self>, data: Vec<u8>) -> PyRefMut<Self> {
        slf.data.extend_from_slice(&data);
        slf
    }
    
    /// Build the final input data bytes
    /// 
    /// Returns the serialized bytes ready to pass to prove() or Composer.
    pub fn build(&self) -> Vec<u8> {
        self.data.clone()
    }
    
    /// Get the current size of the serialized data
    #[getter]
    pub fn size(&self) -> usize {
        self.data.len()
    }
    
    /// Clear all data and start over
    pub fn clear(&mut self) {
        self.data.clear();
    }
    
    /// Write CBOR with length frame (Pattern C: Safe mixing)
    /// 
    /// Writes: [u64 length in little-endian][CBOR bytes]
    /// This allows safely mixing CBOR with raw fields.
    /// 
    /// **Python code:**
    /// ```python
    /// builder.write_cbor_frame(cbor2.dumps(data, canonical=True))
    /// builder.write_u32(42)  # Can safely add raw fields after
    /// ```
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// // Read frame length
    /// let mut len_bytes = [0u8; 8];
    /// env::read_slice(&mut len_bytes);
    /// let len = u64::from_le_bytes(len_bytes) as usize;
    /// 
    /// // Read CBOR data
    /// let mut cbor_data = vec![0u8; len];
    /// env::read_slice(&mut cbor_data);
    /// let input: Input = minicbor::decode(&cbor_data).unwrap();
    /// 
    /// // Now can safely read more fields
    /// let mut n = [0u8; 4];
    /// env::read_slice(&mut n);
    /// let extra = u32::from_le_bytes(n);
    /// ```
    pub fn write_cbor_frame(mut slf: PyRefMut<Self>, cbor_bytes: Vec<u8>) -> PyRefMut<Self> {
        let len = cbor_bytes.len() as u64;
        slf.data.extend_from_slice(&len.to_le_bytes());
        slf.data.extend_from_slice(&cbor_bytes);
        slf
    }
    
    /// Write raw bytes with length frame (Pattern C: Safe for variable-length)
    /// 
    /// Writes: [u64 length in little-endian][raw bytes]
    /// 
    /// **Guest code (Rust):**
    /// ```rust
    /// let mut len_bytes = [0u8; 8];
    /// env::read_slice(&mut len_bytes);
    /// let len = u64::from_le_bytes(len_bytes) as usize;
    /// let mut data = vec![0u8; len];
    /// env::read_slice(&mut data);
    /// ```
    pub fn write_frame(mut slf: PyRefMut<Self>, data: Vec<u8>) -> PyRefMut<Self> {
        let len = data.len() as u64;
        slf.data.extend_from_slice(&len.to_le_bytes());
        slf.data.extend_from_slice(&data);
        slf
    }
}

// Internal methods for use from Rust code (e.g., Composer)
impl InputBuilder {
    /// Internal version of write_cbor that doesn't need PyRefMut
    pub(crate) fn write_cbor_internal(&mut self, cbor_bytes: Vec<u8>) {
        self.data.extend_from_slice(&cbor_bytes);
    }
    
    /// Internal version of write_cbor_frame that doesn't need PyRefMut
    pub(crate) fn write_cbor_frame_internal(&mut self, cbor_bytes: Vec<u8>) {
        let len = cbor_bytes.len() as u64;
        self.data.extend_from_slice(&len.to_le_bytes());
        self.data.extend_from_slice(&cbor_bytes);
    }
    
    /// Internal version of write_u32 that doesn't need PyRefMut
    pub(crate) fn write_u32_internal(&mut self, value: u32) {
        self.data.extend_from_slice(&value.to_le_bytes());
    }
    
    /// Internal version of write_u64 that doesn't need PyRefMut
    pub(crate) fn write_u64_internal(&mut self, value: u64) {
        self.data.extend_from_slice(&value.to_le_bytes());
    }
    
    /// Internal version of write_bytes32 that doesn't need PyRefMut
    pub(crate) fn write_bytes32_internal(&mut self, data: Vec<u8>) -> Result<(), String> {
        if data.len() != 32 {
            return Err(format!("write_bytes32 requires exactly 32 bytes, got {}", data.len()));
        }
        self.data.extend_from_slice(&data);
        Ok(())
    }
    
    /// Internal version of write_raw_bytes that doesn't need PyRefMut
    pub(crate) fn write_raw_bytes_internal(&mut self, data: Vec<u8>) {
        self.data.extend_from_slice(&data);
    }
    
    /// Internal version of write_frame that doesn't need PyRefMut
    pub(crate) fn write_frame_internal(&mut self, data: Vec<u8>) {
        let len = data.len() as u64;
        self.data.extend_from_slice(&len.to_le_bytes());
        self.data.extend_from_slice(&data);
    }
}