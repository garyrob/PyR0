# PyR0 - Python Interface for RISC Zero zkVM

[![Version](https://img.shields.io/badge/version-0.7.0-orange)](https://github.com/garyrob/PyR0/releases)
**⚠️ Experimental Alpha - Apple Silicon Only**

Python bindings for [RISC Zero](https://www.risczero.com/) zkVM, enabling zero-knowledge proof generation and verification from Python.

> **⚠️ IMPORTANT**: This is an experimental alpha release (v0.7.0) currently targeting Apple Silicon (M1/M2/M3) Macs only.
> 
> **🚧 TESTING STATUS**: The v0.7.0 API is a major refactor introducing safe proof composition. **Many unit tests are still needed** to validate the new Composer API, claim abstractions, and error handling. Use with caution in production.

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
- Build Merkle trees with Poseidon hash for ZK circuits
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

### Building from Source

```bash
# Clone the repository
git clone https://github.com/garyrob/PyR0.git
cd PyR0

# Build and install with uv
uv tool run maturin build --release
uv pip install --force-reinstall target/wheels/PyR0-*-macosx_11_0_arm64.whl
```

For development with editable installs, see [CLAUDE.md](CLAUDE.md) for important notes about uv's behavior.

## Features

### Building Guest Programs

PyR0 can build RISC Zero guest programs directly:

```python
import pyr0

# Build a guest program (always rebuilds to ensure up-to-date)
elf_path = pyr0.build_guest("path/to/guest", "binary-name")

# Auto-detect binary name from Cargo.toml
elf_path = pyr0.build_guest("path/to/guest")

# Build in debug mode (faster compile, slower execution)
elf_path = pyr0.build_guest("path/to/guest", release=False)
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

# Get the journal (public outputs) as a property
journal = receipt.journal

# Verify the proof
receipt.verify()

# Access the image ID
image_id = image.id
```

### Merkle Trees with Poseidon Hash

Build sparse Merkle trees compatible with zero-knowledge circuits:

```python
import merkle_py

# Create a sparse Merkle tree
tree = merkle_py.MerkleTree()

# Insert keys
tree.insert("0x0000000000000000000000000000000000000000000000000000000000000001")
tree.insert("0x0000000000000000000000000000000000000000000000000000000000000002")

# Get the root
root = tree.root()

# Generate a Merkle proof (16 levels for Noir compatibility)
siblings, bits = tree.merkle_path_16(key)

# Use Poseidon hash directly
hash_result = merkle_py.poseidon_hash([input1, input2])
```

### Data Serialization

PyR0 provides serialization helpers for sending data to RISC Zero guest programs. The choice of serialization method depends on how your guest reads the data:

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

# For Merkle proofs with 2LA-style commitments (uses env::read_slice() format)
# Note: Expects exactly 16 siblings for a 16-level tree
input_data = serialization.merkle_commitment_input(k_pub, r, e, siblings, indices)
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

#### Step 1: Set Up Your Inner Guest

Create `inner_guest/src/main.rs`:
```rust
use risc0_zkvm::guest::env;

fn main() {
    // Read two numbers from the host
    let a: u32 = env::read();
    let b: u32 = env::read();
    
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
    // Read expected values from host using read_slice for raw bytes
    let mut sum_bytes = [0u8; 4];
    env::read_slice(&mut sum_bytes);
    let expected_sum = u32::from_le_bytes(sum_bytes);
    
    // Read the inner guest's image ID (32 bytes)
    let mut inner_image_id = [0u8; 32];
    env::read_slice(&mut inner_image_id);
    
    // Verify the inner proof (assumption)
    // env::verify takes the expected journal bytes and image ID
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
inner_image_id = inner_image.image_id_bytes
outer_image_id = pyr0.compute_image_id_hex(outer_elf)

# 2. Generate the inner proof
# Prepare input: two u32 values
a, b = 3, 5
inner_input = pyr0.serialization.to_u32(a) + pyr0.serialization.to_u32(b)
inner_receipt = pyr0.prove(inner_image, inner_input)

# 3. Extract the sum from inner proof's journal
# The journal contains the raw bytes of what was committed
journal_bytes = inner_receipt.journal_bytes
sum_value = struct.unpack('<I', journal_bytes[:4])[0]  # Little-endian u32
print(f"Inner proof computed: {a} + {b} = {sum_value}")

# 4. Create a Composer with the inner proof as an assumption
comp = pyr0.Composer(outer_image)
comp.assume(inner_receipt)  # KEY STEP: Add the inner proof

# 5. Provide input data for the outer guest using typed writers
comp.write_u32(sum_value)           # Expected sum (4 bytes)
comp.write_image_id(inner_image_id) # Inner image ID (32 bytes)

# 6. Generate the composed proof (defaults to succinct to resolve assumptions)
outer_receipt = comp.prove()  # or comp.prove(kind=pyr0.ReceiptKind.SUCCINCT)

# 7. Extract and verify the final result
outer_journal = outer_receipt.journal_bytes
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
journal_bytes = receipt.journal_bytes
value = struct.unpack('<I', journal_bytes[:4])[0]  # Little-endian

# For multiple values, track offsets
first_u32 = struct.unpack('<I', journal_bytes[0:4])[0]
second_u32 = struct.unpack('<I', journal_bytes[4:8])[0]
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

# 1. Generate two independent proofs
left_receipt = pyr0.prove_with_opts(left_image, left_input, succinct=True)
right_receipt = pyr0.prove_with_opts(right_image, right_input, succinct=True)

# 2. Create aggregator that will verify both
comp = pyr0.Composer(aggregator_image)

# 3. Add both receipts as assumptions (automatically deduped if identical)
comp.assume(left_receipt)   # Must be succinct or groth16
comp.assume(right_receipt)  # Must be succinct or groth16

# 4. Write the data the aggregator guest expects
# The guest will call env::verify() twice, once for each proof
comp.write_image_id(left_image.id)
comp.write_slice(left_receipt.journal_bytes)
comp.write_image_id(right_image.id) 
comp.write_slice(right_receipt.journal_bytes)

# 5. Register expected verifications for preflight checking
comp.expect_verification(left_image.id, left_receipt.journal_bytes)
comp.expect_verification(right_image.id, right_receipt.journal_bytes)

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

### Merkle Zero-Knowledge Proofs

See [demo/merkle_zkp_demo.py](demo/merkle_zkp_demo.py) for a complete example of:
- Building Merkle trees with user commitments
- Generating zero-knowledge proofs of membership
- Privacy-preserving authentication (proving you're in a set without revealing which member)

## Project Structure

```
PyR0/
├── src/               # Rust source code
│   ├── lib.rs        # Main PyO3 bindings
│   ├── image.rs      # RISC Zero image handling
│   ├── segment.rs    # Proof generation
│   └── receipt.rs    # Proof verification
├── merkle/           # Merkle tree module
│   └── src/          # Merkle tree implementation
├── demo/             # Example scripts
│   ├── merkle_zkp_demo.py     # Merkle ZKP demonstration
│   ├── merkle_proof_guest/    # RISC Zero guest for Merkle proofs
│   └── ed25519_demo.py        # Ed25519 verification demo
├── test/             # Test scripts
└── CLAUDE.md         # Development notes
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

## Development

This project uses [maturin](https://www.maturin.rs/) for building Python extensions from Rust. Key commands:

```bash
# Build release wheel
uv tool run maturin build --release

# Install the built wheel (force reinstall to avoid cache issues)
uv pip install --force-reinstall target/wheels/PyR0-0.2.0-*.whl

# Run tests/demos
uv run demo/ed25519_demo.py
uv run demo/merkle_zkp_demo.py
uv run test/test_merkle_zkp.py
```

### Important Build Notes

After making changes to ANY file (Rust or Python), you must rebuild and reinstall:
1. Build: `uv tool run maturin build --release`
2. Install: `uv pip install --force-reinstall target/wheels/PyR0-*.whl`

The `--force-reinstall` flag is crucial to ensure you're using the latest version.

## Acknowledgments

This project is based on the original [PyR0](https://github.com/l2iterative/pyr0prover-python) by L2 Iterative, which focused on distributed proof generation using Dask/Ray. The current fork extends PyR0 with additional features for zero-knowledge proof development, including Merkle tree support and improved guest program interfaces.

## License

This project is dual-licensed under either:

- MIT license ([LICENSE](LICENSE))
- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))

You may choose either license for your use case.

See [NOTICE](NOTICE) for attribution and details about the original project.