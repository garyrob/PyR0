# PyR0 - Python Interface for RISC Zero zkVM

[![Version](https://img.shields.io/badge/version-0.8.0-green)](https://github.com/garyrob/PyR0/releases)
**⚠️ Experimental Alpha - Apple Silicon Only**

Python bindings for [RISC Zero](https://www.risczero.com/) zkVM, enabling zero-knowledge proof generation and verification from Python.

> **⚠️ IMPORTANT**: This is an experimental release (v0.8.0) currently targeting Apple Silicon (M1/M2/M3) Macs only.
> 
> **🚧 ALPHA STATUS**: v0.8.0 removes all placeholder APIs and enforces production-safe defaults (release-only builds, no mocking). Still experimental and limited to Apple Silicon.

## Testing Requirements

The following components need comprehensive unit tests:

- [ ] **Composer API** - All writer methods, assumption validation, preflight checks
- [ ] **Claim abstraction** - Property access, matching logic
- [ ] **ReceiptKind enum** - Proper type checking in prove()
- [ ] **Polymorphic verify()** - All input types (bytes, hex, Image)
- [ ] **Error hierarchy** - Custom exceptions raised correctly
- [ ] **Deduplication** - Assumption dedup by claim digest
- [ ] **Tree aggregation** - Multiple env::verify() calls
- [ ] **VerifierContext** - Batch verification efficiency
- [ ] **Type stubs** - IDE autocomplete and mypy validation
- [ ] **Edge cases** - Invalid inputs, malformed data, resource limits

## Overview

PyR0 provides a Python interface to RISC Zero's zero-knowledge virtual machine, allowing you to:
- Execute RISC Zero guest programs from Python
- Generate and verify zero-knowledge proofs
- Serialize data for guest program inputs

### Architecture

PyR0 bridges Python and RISC Zero zkVM:

1. **Host (Python)**: Prepares input data, loads guest programs, generates proofs
2. **Guest (Rust)**: Executes in zkVM, reads input, writes output to journal
3. **Proof**: Cryptographic evidence that the guest executed correctly

The typical workflow:
1. Write a Rust guest program that performs your computation
2. Compile it to RISC-V ELF binary
3. Use PyR0 to load the ELF, provide input, and generate a proof
4. Share the proof and journal (public outputs) for verification

## Guest Program Development

### Basic Guest Setup

A minimal RISC Zero guest program requires proper configuration:

**Cargo.toml:**
```toml
[package]
name = "my-guest"
version = "0.1.0"
edition = "2021"

[dependencies]
# Basic setup - works for simple guests
risc0-zkvm = { version = "1.2", default-features = false, features = ["std"] }
```

### Memory Management

⚠️ **Critical for complex guests**: The default bump allocator never frees memory, causing "Out of memory!" errors even with moderate data.

Enable the heap allocator for guests that:
- Process variable-length data
- Use collections (Vec, HashMap, etc.)
- Perform string operations
- Run iterative algorithms

```toml
[dependencies]
risc0-zkvm = { version = "1.2", default-features = false, features = ["std", "heap-embedded-alloc"] }
```

*Note: The heap allocator adds ~5% cycle overhead but prevents memory exhaustion.*

### Common Guest Patterns

**Reading Input:**
```rust
// For raw bytes (most efficient, works with pyr0.prove(image, raw_bytes))
use std::io::Read;
let mut buffer = Vec::new();
env::stdin().read_to_end(&mut buffer).unwrap();

// For serialized data (when using PyR0 serialization helpers)
let data: MyStruct = env::read();
```

**Writing to Journal:**
```rust
// Simple values
env::commit(&my_u32);

// Complex structures (using Borsh)
use borsh::BorshSerialize;
let output = MyOutput { /* ... */ };
env::commit_slice(&borsh::to_vec(&output).unwrap());
```

## Installation

### System Requirements

**This alpha release requires:**
- Apple Silicon Mac (M1, M2, or M3)
- macOS 11.0 or later
- Python 3.8.3+
- Rust toolchain with cargo
- RISC Zero toolchain (`cargo risczero` installed via `cargo install cargo-risczero`)
- [uv](https://docs.astral.sh/uv/) package manager

### Installation for Users

#### From PyPI (Coming Soon)

Once published, you'll be able to install PyR0 directly:

```bash
# Install PyR0 as a dependency
uv add PyR0==0.8.0
# or with pip
pip install PyR0==0.8.0
```

#### From Source (For Users)

If you want to use PyR0 from source in your project:

```bash
# Clone and build
git clone https://github.com/garyrob/PyR0.git
cd PyR0
uv tool run maturin build --release

# In your project directory
cd /path/to/your/project
uv add PyR0==0.8.0 --find-links /path/to/PyR0/target/wheels
```


## Features

### Building Guest Programs

PyR0 can build RISC Zero guest programs directly:

```python
import pyr0

# Build a guest program (always rebuilds to ensure up-to-date)
elf_path = pyr0.build_guest("path/to/guest", "binary-name")

# Auto-detect binary name from Cargo.toml
elf_path = pyr0.build_guest("path/to/guest")

# Always builds in release mode for optimal performance
# Debug builds are not supported due to severe performance issues
```

The `build_guest` function:
- Always rebuilds to ensure the ELF is up-to-date
- Handles both standard (embed_methods) and direct build structures
- Automatically detects the correct build method
- Returns the path to the built ELF file
- Raises `GuestBuildFailedError` if compilation fails
- Raises `InvalidGuestDirectoryError` if the directory is invalid
- Raises `ElfNotFoundError` if the ELF isn't found after building

### Core RISC Zero Operations

Execute guest programs and generate proofs:

```python
import pyr0

# Option 1: Build and load a guest program
elf_path = pyr0.build_guest("path/to/guest", "binary-name")
with open(elf_path, "rb") as f:
    elf_data = f.read()
image = pyr0.load_image(elf_data)

# Option 2: Load a pre-built ELF
with open("guest_program.elf", "rb") as f:
    elf_data = f.read()
image = pyr0.load_image(elf_data)

# One-step proof generation (execution + proof)
input_data = b"your input data"  # Direct bytes, no wrapper needed
receipt = pyr0.prove(image, input_data)

# For unconditional proofs (no unresolved assumptions):
receipt = pyr0.prove_succinct(image, input_data)
# Equivalent to: pyr0.prove(image, input_data, kind=pyr0.ReceiptKind.SUCCINCT)

# Get the journal (public outputs)
journal = receipt.journal

# Verify the proof
receipt.verify()  # Or receipt.verify(image.id_hex) to verify against expected image

# Access the image ID
image_id = image.id       # 32 bytes
image_id_hex = image.id_hex  # Hex string
```


### Data Serialization

PyR0 provides multiple approaches for sending data to RISC Zero guest programs. **Choose ONE pattern per guest** to avoid serialization mismatches:

#### InputBuilder API - Three Safe Patterns

##### Pattern A: CBOR-Only (Recommended for complex data)

Use when your guest needs structured data with variable-length fields.

**Important:** `write_cbor(b)` and `write_cbor_frame(b)` expect **CBOR-encoded bytes**. Always encode your Python objects first:

```python
import pyr0
from cbor2 import dumps as cbor_dumps

builder = pyr0.InputBuilder()
# Encode your data to CBOR bytes with canonical settings for determinism
data = {"user_id": 123, "values": [1, 2, 3], "config": {"threshold": 100}}
cbor_bytes = cbor_dumps(data, canonical=True)
builder.write_cbor(cbor_bytes)  # Pass the encoded bytes
input_data = builder.build()
receipt = pyr0.prove(image, input_data)
```

**Guest code:**
```rust
use minicbor::{Decode, Encode};
use std::io::Read;

#[derive(Decode, Encode)]
struct Input {
    #[n(0)] user_id: u32,
    #[n(1)] values: Vec<u32>,
    #[n(2)] config: Config,
}

fn main() {
    let mut buf = Vec::new();
    env::stdin().read_to_end(&mut buf).unwrap();
    let input: Input = minicbor::decode(&buf).unwrap();  // Entire stdin is ONE CBOR object
}
```

##### Pattern B: Raw-Only (Fast for fixed-size data)

Use when all data has known fixed sizes:

```python
builder = pyr0.InputBuilder()
builder.write_u32(42)           # 4 bytes, little-endian
builder.write_u64(1000000)      # 8 bytes, little-endian  
builder.write_bytes32(key)      # Enforces exactly 32 bytes
input_data = builder.build()
```

**Guest code:**
```rust
fn main() {
    // Read each field with exact size
    let mut n = [0u8; 4];
    env::read_slice(&mut n);
    let value = u32::from_le_bytes(n);
    
    let mut m = [0u8; 8];
    env::read_slice(&mut m);
    let large = u64::from_le_bytes(m);
    
    let mut key = [0u8; 32];
    env::read_slice(&mut key);
}
```

##### Pattern C: Framed (Safe mixing of CBOR and raw)

Use when you need both structured and raw data:

```python
from cbor2 import dumps as cbor_dumps

builder = pyr0.InputBuilder()
# CBOR with frame: [8-byte length][CBOR data]
config = {"user_id": 123, "settings": {...}}
cbor_bytes = cbor_dumps(config, canonical=True)
builder.write_cbor_frame(cbor_bytes)  # Framed for safe mixing
# Raw fields after the frame
builder.write_u32(42)
builder.write_raw_bytes(signature)  # Exactly 64 bytes
input_data = builder.build()
```

**Guest code:**
```rust
fn main() {
    // Read CBOR frame
    let mut len_bytes = [0u8; 8];
    env::read_slice(&mut len_bytes);
    let len = u64::from_le_bytes(len_bytes) as usize;
    
    let mut cbor_data = vec![0u8; len];
    env::read_slice(&mut cbor_data);
    let config: Config = minicbor::decode(&cbor_data).unwrap();
    
    // Read raw fields after frame
    let mut n = [0u8; 4];
    env::read_slice(&mut n);
    let extra = u32::from_le_bytes(n);
    
    let mut sig = [0u8; 64];
    env::read_slice(&mut sig);
}
```

#### InputBuilder Wire Format Reference

**Format:** Writes are concatenated byte-for-byte in order. No padding or alignment is inserted.

| Method | Bytes on Wire | Guest Read Method | Notes |
|--------|--------------|-------------------|--------|
| `write_u32(x)` | 4 bytes, **little-endian** | `read_slice(&mut [u8;4])` → `u32::from_le_bytes()` | Fixed size |
| `write_u64(x)` | 8 bytes, **little-endian** | `read_slice(&mut [u8;8])` → `u64::from_le_bytes()` | Fixed size |
| `write_bytes32(b)` | 32 raw bytes | `read_slice(&mut [u8;32])` | Enforces exactly 32 bytes |
| `write_image_id(id)` | 32 raw bytes | `read_slice(&mut [u8;32])` | Alias for write_bytes32 |
| `write_raw_bytes(b)` | len(b) raw bytes | `read_slice(&mut [u8;N])` | Guest must know exact size |
| `write_cbor(b)` | CBOR bytes, **no prefix** | `minicbor::decode(&all_stdin)` | Use alone (Pattern A); pass CBOR-encoded bytes |
| `write_cbor_frame(b)` | [8-byte len LE] + CBOR | Read len, then decode | Safe for mixing (Pattern C); pass CBOR-encoded bytes |
| `write_frame(b)` | [8-byte len LE] + bytes | Read len, then bytes | Variable-length raw data |

**⚠️ Critical Rules:**
- **Never mix** `write_cbor()` with other methods - the decoder will fail
- **Always use canonical CBOR** (`canonical=True`) for deterministic encoding
- **Use frames** (`write_cbor_frame()`) when mixing CBOR with raw fields
- All integers are **little-endian**

#### Legacy Serialization Helpers (For env::read)

These helpers match `env::read()` semantics: fixed-size primitives are little-endian; variable-length types include a length prefix. They are kept for backward compatibility but **InputBuilder patterns above are recommended** for new code:

#### For Guests Using `env::read()`

These helpers add length prefixes and are designed for serde deserialization:

```python
from pyr0 import serialization

# These work with env::read() in the guest
data = serialization.to_vec_u8(bytes_data)  # Vec<u8> with length prefix
data = serialization.to_u32(value)          # u32 (4 bytes, little-endian)
data = serialization.to_u64(value)          # u64 (8 bytes, little-endian)
data = serialization.to_string(text)        # String with 8-byte length prefix
data = serialization.to_bool(value)         # bool (single byte: 0 or 1)

# Guest code would use:
# let data: Vec<u8> = env::read();
# let value: u32 = env::read();
# let text: String = env::read();
```

#### For Guests Using `env::read_slice()`

These helpers provide raw bytes without length prefixes:

```python
# Fixed-size arrays (no length prefix)
data = serialization.to_bytes32(data)       # [u8; 32] - exactly 32 bytes
data = serialization.to_bytes64(data)       # [u8; 64] - exactly 64 bytes
data = serialization.raw_bytes(data)        # Raw bytes, no transformation

# Guest code would use:
# let mut buffer = [0u8; 32];
# env::read_slice(&mut buffer);
```

#### Convenience Functions

Pre-built serializers for common cryptographic operations:

```python
# For Ed25519 signature verification (uses env::read() format)
input_data = serialization.ed25519_input(public_key, signature, message)

```

#### Choosing Between `env::read()` and `env::read_slice()`

**Use `env::read()` when:**
- Data sizes are variable
- You want automatic deserialization
- You're using standard Rust types (Vec, String, etc.)
- You don't know the exact size in advance

**Use `env::read_slice()` when:**
- Data size is fixed and known
- You want maximum efficiency (no overhead)
- You're working with raw bytes
- You want to avoid serde overhead

**Example: Sending mixed data types**

```python
# Python host code
from pyr0 import serialization

# Combine different serialization methods
input_data = b""
input_data += serialization.to_u32(42)           # 4 bytes (for env::read)
input_data += serialization.to_bytes32(key)      # 32 bytes (for env::read_slice)
input_data += serialization.to_string("hello")   # Variable (for env::read)

receipt = pyr0.prove(image, input_data)
```

```rust
// Rust guest code
use risc0_zkvm::guest::env;

fn main() {
    // Read the u32 with serde
    let number: u32 = env::read();
    
    // Read the fixed array with read_slice
    let mut key = [0u8; 32];
    env::read_slice(&mut key);
    
    // Read the string with serde
    let text: String = env::read();
}
```

### Journal Deserialization

For cross-language compatibility, guest programs should use Borsh serialization:

```python
from borsh_construct import CStruct, U8, U64

# Define schema matching your Rust struct
OutputSchema = CStruct(
    "field1" / U8[32],   # [u8; 32] in Rust
    "field2" / U64,      # u64 in Rust
)

# Parse journal from receipt
journal = receipt.journal  # Access as property
output = OutputSchema.parse(journal)
```

## Proof Composition - Complete Guide

PyR0 enables proof composition using RISC Zero's assumption-based recursion model. This powerful feature allows one zkVM guest to verify proofs from another guest, enabling complex multi-step computations with a single final verification.

### Understanding Proof Composition

Proof composition solves a fundamental challenge: how can we break complex computations into smaller, manageable pieces while maintaining cryptographic guarantees? 

The traditional approach would require verifying each proof separately, which is expensive. PyR0's composition model uses "lazy verification" - the outer proof doesn't directly verify the inner proof but adds it as an assumption that gets verified when the final proof is generated.

#### The Three-Part Architecture

1. **Inner Guest**: Performs the initial computation and generates a proof
2. **Outer Guest**: Verifies the inner proof's journal matches expectations and performs additional computation
3. **Final Proof**: A single proof that cryptographically guarantees both computations are valid

The key insight: when you verify the outer receipt, RISC Zero automatically ensures all assumptions (inner proofs) were valid. You get the security of multiple proofs with a single verification.

### Complete Working Example

#### Using the Simplified API with Safe Patterns

PyR0 v0.7.0 introduces a simplified API for proof composition using consistent patterns:

```python
import pyr0
import struct

# Build both guests
inner_image = pyr0.load_image(pyr0.build_guest("inner_guest"))
outer_image = pyr0.load_image(pyr0.build_guest("outer_guest"))

# 1. Generate inner proof (Pattern B: Raw-only)
inner_builder = pyr0.InputBuilder()
inner_builder.write_u32(3).write_u32(5)  # Two fixed-size values
inner_receipt = pyr0.prove(inner_image, inner_builder.build())

# 2. Extract sum from inner proof's journal
journal = inner_receipt.journal
expected_sum = struct.unpack('<I', journal[:4])[0]  # 8

# 3. Compose with outer proof (Pattern B: Raw-only for consistency)
comp = pyr0.Composer(outer_image)
comp.assume(inner_receipt)

# Write raw fields that the outer guest expects
comp.write_u32(expected_sum)      # 4 bytes
comp.write_bytes32(inner_image.id) # 32 bytes (enforces length)

# 4. Generate and verify composed proof
outer_receipt = comp.prove()
outer_receipt.verify(outer_image)
print("✓ Composed proof verified!")
```

#### Step 1: Set Up Your Inner Guest

Create `inner_guest/src/main.rs`:
```rust
use risc0_zkvm::guest::env;

fn main() {
    // Pattern B: Raw-only - read fixed-size values
    let mut a_bytes = [0u8; 4];
    env::read_slice(&mut a_bytes);
    let a = u32::from_le_bytes(a_bytes);
    
    let mut b_bytes = [0u8; 4];
    env::read_slice(&mut b_bytes);
    let b = u32::from_le_bytes(b_bytes);
    
    // Perform computation
    let sum = a + b;
    
    // Commit result to journal (public output)
    env::commit(&sum);
}
```

#### Step 2: Set Up Your Outer Guest

Create `outer_guest/src/main.rs`:
```rust
use risc0_zkvm::guest::env;

fn main() {
    // Pattern B: Raw-only - consistent with inner guest
    // Read expected sum (4 bytes)
    let mut sum_bytes = [0u8; 4];
    env::read_slice(&mut sum_bytes);
    let expected_sum = u32::from_le_bytes(sum_bytes);
    
    // Read the inner guest's image ID (32 bytes)
    let mut inner_image_id = [0u8; 32];
    env::read_slice(&mut inner_image_id);
    
    // Verify the inner proof (assumption)
    // env::verify takes the image ID and expected journal bytes
    // This creates an assumption that gets verified when the outer proof is generated
    let expected_journal = risc0_zkvm::serde::to_vec(&expected_sum).unwrap();
    env::verify(inner_image_id, &expected_journal).unwrap();
    
    // Now we can trust expected_sum came from the verified inner proof
    // Perform additional computation
    let result = expected_sum * 2;
    
    // Commit our result
    env::commit(&result);
}
```

#### Step 3: Python Host Code

```python
import pyr0
import struct

# 1. Build and load both guest programs
inner_elf = pyr0.build_guest("inner_guest")
outer_elf = pyr0.build_guest("outer_guest")
inner_image = pyr0.load_image(inner_elf)
outer_image = pyr0.load_image(outer_elf)

# Save image IDs for verification
inner_image_id = inner_image.id  # 32 bytes
outer_image_id = outer_image.id_hex  # hex string

# 2. Generate the inner proof
# Prepare input: two u32 values
a, b = 3, 5
inner_input = pyr0.serialization.to_u32(a) + pyr0.serialization.to_u32(b)
inner_receipt = pyr0.prove(inner_image, inner_input)

# 3. Extract the sum from inner proof's journal
# The journal contains the raw bytes of what was committed
journal = inner_receipt.journal
sum_value = struct.unpack('<I', journal[:4])[0]  # Little-endian u32
print(f"Inner proof computed: {a} + {b} = {sum_value}")

# 4. Create a Composer with the inner proof as an assumption
comp = pyr0.Composer(outer_image)
comp.assume(inner_receipt)  # KEY STEP: Add the inner proof

# 5. Provide input data for the outer guest using typed writers (Pattern B: Raw-only)
comp.write_u32(sum_value)           # Expected sum (4 bytes)
comp.write_bytes32(inner_image_id)  # Inner image ID (32 bytes, enforced)

# 6. Generate the composed proof (defaults to succinct to resolve assumptions)
outer_receipt = comp.prove()  # or comp.prove(kind=pyr0.ReceiptKind.SUCCINCT)

# 7. Extract and verify the final result
outer_journal = outer_receipt.journal
final_result = struct.unpack('<I', outer_journal[:4])[0]
print(f"Outer proof computed: {sum_value} * 2 = {final_result}")

# 8. Verify the composed proof
# This single verification ensures BOTH computations are valid!
outer_receipt.verify(outer_image_id)  # Can use hex, bytes, or Image
print("✓ Composed proof verified - both computations are cryptographically proven!")
```

### Critical Implementation Details

#### The Composer Pattern

The `Composer` class provides a safer API for proof composition:
- Use `comp.assume(receipt)` to add proofs that need verification
- Use typed writers (`write_u32()`, `write_bytes32()`, etc.) for type-safe input
- Use `comp.prove(kind="succinct")` to resolve assumptions
- In the guest, use `env::read_slice()` for raw bytes from the typed writers

#### Journal Data Extraction

When extracting data from journals:
```python
# For a u32 value committed in the guest
journal = receipt.journal
value = struct.unpack('<I', journal[:4])[0]  # Little-endian

# For multiple values, track offsets
first_u32 = struct.unpack('<I', journal[0:4])[0]
second_u32 = struct.unpack('<I', journal[4:8])[0]
```

#### Image ID Verification

The outer guest must verify the inner proof came from the expected program:
```rust
// In the outer guest
env::verify(inner_image_id, &expected_journal).unwrap();
```

This ensures you're not accepting proofs from arbitrary programs.

### Advanced Patterns

#### Tree Aggregation (Multiple Verifications)

The Composer API fully supports aggregating multiple proofs in a single guest. This is essential for building proof trees where one guest verifies multiple inner proofs:

```python
# Example: Aggregator that verifies two inner proofs
import pyr0

# 1. Generate two independent proofs (must be unconditional)
left_receipt = pyr0.prove_succinct(left_image, left_input)
right_receipt = pyr0.prove_succinct(right_image, right_input)

# 2. Create aggregator that will verify both
comp = pyr0.Composer(aggregator_image)

# 3. Add both receipts as assumptions (automatically deduped if identical)
comp.assume(left_receipt)   # Must be succinct or groth16
comp.assume(right_receipt)  # Must be succinct or groth16

# 4. Write the data the aggregator guest expects
# The guest will call env::verify() twice, once for each proof
comp.write_image_id(left_image.id)
comp.write_frame(left_receipt.journal)
comp.write_image_id(right_image.id) 
comp.write_frame(right_receipt.journal)

# 5. Register expected verifications for preflight checking
comp.expect_verification(left_image.id, left_receipt.journal)
comp.expect_verification(right_image.id, right_receipt.journal)

# 6. Generate the aggregated proof (defaults to succinct)
# This runs the recursion program to resolve both assumptions
aggregated = comp.prove()  # Will raise if preflight checks fail

# The aggregated receipt proves both inner computations are valid!
print(f"Aggregated proof kind: {aggregated.kind}")  # ReceiptKind.SUCCINCT
print(f"Is unconditional: {aggregated.is_unconditional}")  # True
```

The corresponding aggregator guest would look like:
```rust
use risc0_zkvm::guest::env;

fn main() {
    // Read and verify left proof
    let mut left_image_id = [0u8; 32];
    env::read_slice(&mut left_image_id);
    let mut left_journal_len = [0u8; 8];
    env::read_slice(&mut left_journal_len);
    let len = u64::from_le_bytes(left_journal_len) as usize;
    let mut left_journal = vec![0u8; len];
    env::read_slice(&mut left_journal);
    
    env::verify(left_image_id, &left_journal).unwrap();
    
    // Read and verify right proof  
    let mut right_image_id = [0u8; 32];
    env::read_slice(&mut right_image_id);
    let mut right_journal_len = [0u8; 8];
    env::read_slice(&mut right_journal_len);
    let len = u64::from_le_bytes(right_journal_len) as usize;
    let mut right_journal = vec![0u8; len];
    env::read_slice(&mut right_journal);
    
    env::verify(right_image_id, &right_journal).unwrap();
    
    // Perform aggregated computation
    // Both proofs are now verified!
    env::commit(&"Both proofs valid");
}
```

#### Multiple Assumptions (Simplified)

For simpler cases where you're just verifying multiple instances of the same guest:
```python
comp = pyr0.Composer(aggregator_image)
comp.assume(proof1)
comp.assume(proof2)
comp.assume(proof3)
# All three proofs will be verified with the final proof
receipt = comp.prove()
```

#### Conditional Composition

The outer guest can make decisions based on inner proof data:
```rust
// In outer guest
if expected_sum > 100 {
    // One computation path
} else {
    // Another computation path
}
```

#### Recursive Composition

You can chain compositions:
```python
# First composition
comp1 = pyr0.Composer(middle_image)
comp1.assume(inner_receipt)
comp1.write_u32(value)
middle_receipt = comp1.prove(kind="succinct")

# Second composition
comp2 = pyr0.Composer(outer_image)
comp2.assume(middle_receipt)
comp2.write_u32(another_value)
outer_receipt = comp2.prove(kind="succinct")
```

### Use Cases

1. **Multi-step Computations**: Break complex algorithms into verifiable steps
2. **Privacy-Preserving Pipelines**: Different parties prove different parts without revealing internals
3. **Modular Verification**: Build libraries of verified components
4. **Delegation**: Prove you correctly processed someone else's proven computation
5. **Aggregation**: Combine multiple proofs into a single verifiable result

### Performance Considerations

- **Assumption Cost**: Each assumption adds ~200-500ms to proof generation
- **Memory**: Composed proofs are larger (~2x) than simple proofs
- **Optimization**: Minimize data passed between guests
- **Batching**: Group related computations in single guests when possible

### Security Notes

1. **Always Verify Image IDs**: Never trust journal data without verifying its source
2. **Check Exit Status**: Ensure inner proofs completed successfully
3. **Validate Journals**: Confirm journal format matches expectations
4. **Test Assumptions**: Invalid assumptions will cause proof generation to fail

### Troubleshooting

**"No receipt found to resolve assumption"**: The inner receipt wasn't properly added or is invalid

**"Guest panicked during env::verify"**: The journal data doesn't match what env::verify expects

**"Invalid image ID"**: The image ID bytes are incorrect length (must be exactly 32 bytes)

**Performance issues**: Consider reducing the number of composed proofs or optimizing guest code

## Examples

### Ed25519 Signature Verification

See [demo/ed25519_demo.py](demo/ed25519_demo.py) for a complete example of:
- Building a RISC Zero guest program that verifies Ed25519 signatures
- Generating zero-knowledge proofs of signature validity
- Verifying program identity via ImageID


## Project Structure

```
PyR0/
├── src/               # Rust source code
│   ├── lib.rs        # Main PyO3 bindings
│   ├── image.rs      # RISC Zero image handling
│   ├── receipt.rs    # Proof verification
│   ├── composer.rs   # Proof composition API
│   ├── input_builder.rs # Input data serialization
│   └── verifier.rs   # Batch verification
├── demo/             # Example scripts
│   └── ed25519_demo.py        # Ed25519 verification demo
└── test/             # Test scripts
```

## Common Pitfalls

### Serialization Mismatches

The most common error is mismatched serialization between host and guest:

```python
# WRONG: Host uses to_vec_u8 (adds length prefix)
input_data = serialization.to_vec_u8(my_bytes)
```

```rust
// WRONG: Guest uses read_slice (expects raw bytes)
let mut buffer = [0u8; 32];
env::read_slice(&mut buffer);  // Will read length prefix as data!
```

**Solution**: Match serialization methods:
- `to_vec_u8()` ↔ `env::read::<Vec<u8>>()`
- `to_bytes32()` or `raw_bytes()` ↔ `env::read_slice()`

### Size Mismatches

When using `env::read_slice()`, the buffer size must match exactly:

```rust
// Guest expects exactly 100 bytes
let mut buffer = [0u8; 100];
env::read_slice(&mut buffer);
```

```python
# Host must send exactly 100 bytes
input_data = serialization.raw_bytes(b"x" * 100)  # Correct
input_data = serialization.raw_bytes(b"x" * 99)   # Wrong - too short!
```

### Journal Format

The journal (public output) should use a consistent serialization format. We recommend Borsh for cross-language compatibility:

```rust
// Guest: Write with Borsh
use borsh::BorshSerialize;
let output = MyOutput { ... };
env::commit_slice(&borsh::to_vec(&output)?);
```

```python
# Host: Read with Borsh
from borsh_construct import CStruct
output = OutputSchema.parse(receipt.journal)
```

## Known Issues & Limitations

### v0.7.0 Testing Gaps

This release includes major API improvements but **lacks comprehensive test coverage**:

- **Composer API**: Assumption validation, preflight checks, and error paths are untested
- **Claim abstraction**: New first-class concept needs validation
- **Type safety**: Polymorphic functions and enum parameters need edge case testing  
- **Error handling**: Custom exception hierarchy not fully exercised
- **Composition patterns**: Tree aggregation and multi-verify scenarios untested

**Contributors needed**: Help improve test coverage before using in production!

## Contributing to PyR0

### For Contributors: Development Setup

This section is for developers contributing to PyR0 itself. If you're just using PyR0 in your project, see the Installation section above.

#### Prerequisites

- Rust toolchain with cargo
- [maturin](https://www.maturin.rs/) (installed automatically via uv)
- [uv](https://docs.astral.sh/uv/) package manager
- Python 3.8.3+

#### Development Workflow

PyR0 uses maturin to build Python extensions from Rust. Due to the nature of compiled extensions, we use a specific workflow:

**⚠️ CRITICAL: Always use release builds for PyR0**
```bash
# ALWAYS use this:
uv tool run maturin build --release

# NEVER use this:
uv tool run maturin develop  # ❌ DO NOT USE - causes severe issues
```

**Why `maturin develop` must not be used:**
- **Performance**: Debug builds are 100-1000x slower for RISC Zero operations
- **Guest failures**: Debug mode causes zkVM segment timeouts and memory exhaustion  
- **Test reliability**: Tests may pass in debug but fail in production
- **Missing optimizations**: Critical SIMD and cryptographic optimizations are disabled

```bash
# Clone the repository
git clone https://github.com/garyrob/PyR0.git
cd PyR0

# After making changes to Rust code (src/*.rs):

# 1. Build the wheel (always with --release)
uv tool run maturin build --release

# 2. Sync project dependencies (cbor2, etc.)
uv sync

# 3. Install the built wheel using uv pip
# We use uv pip here because PyR0 builds itself
uv pip install -U PyR0==0.8.0  # Use version from pyproject.toml

# 4. Run tests/demos
uv run python demo/ed25519_demo.py
uv run python test/test_input_builder.py
```

#### Why `uv pip install` for Contributors?

Contributors must use `uv pip install` rather than `uv add` because:
- The project name is `pyr0` (what we're developing)
- We're installing `PyR0` (the built wheel)
- uv correctly prevents self-dependencies with `uv add`
- `uv pip install` installs the compiled wheel directly from `./target/wheels`

#### Project Configuration Explained

The project has special configuration to support this workflow:

**pyproject.toml:**
```toml
[tool.uv]
package = false  # Prevents uv from rebuilding PyR0 on every run

[tool.uv.pip]
find-links = ["./target/wheels"]  # Tells uv pip where to find built wheels
```

This configuration:
- `package = false` stops uv from treating PyR0 as an editable package
- `find-links` allows `uv pip install` to find locally built wheels
- Ensures you're testing the actual compiled extension, not source files

#### Important: Avoid Editable Installs

**Never use editable installs** (`pip install -e .` or default uv behavior) with PyR0. Editable installs will cause Python to import from the source directory instead of the compiled extension module, leading to:
- Missing attributes on PyO3 classes (e.g., `AttributeError: 'pyr0.Image' object has no attribute 'id_hex'`)
- Import errors for new modules
- Tests using outdated code even after rebuilding

Always follow the workflow above: build → sync → pip install.

#### Running Tests

After building and installing:

```bash
# Run individual test files
uv run python test/test_input_builder.py
uv run python test_cbor_serialization.py

# Run demos
uv run python demo/ed25519_demo.py
```

#### Debugging Build Issues

If you encounter issues:

```bash
# Clean build
rm -rf target/wheels/*.whl
uv tool run maturin build --release

# Check what's installed
uv pip list | grep -i pyr0

# Force reinstall if needed
uv pip uninstall PyR0
uv pip install PyR0==0.8.0  # Version from pyproject.toml
```

## Acknowledgments

This project is based on the original [PyR0](https://github.com/l2iterative/pyr0prover-python) by L2 Iterative, which focused on distributed proof generation using Dask/Ray. The current fork extends PyR0 with additional features for zero-knowledge proof development, including Merkle tree support and improved guest program interfaces.

## License

This project is dual-licensed under either:

- MIT license ([LICENSE](LICENSE))
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))

You may choose either license for your use case.

See [NOTICE](NOTICE) for attribution and details about the original project.