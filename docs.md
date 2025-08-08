# PyR0 API Reference

## Core Workflow

The library provides a Python API for generating and verifying zero-knowledge proofs using RISC Zero. Here's the typical workflow:

```python
import pyr0

# 1. Load a RISC Zero program (ELF binary)
with open("program.elf", "rb") as f:
    elf_data = f.read()
image = pyr0.load_image_from_elf(elf_data)

# 2. Execute the program with inputs
input_data = b"your input data here"
segments, session_info = pyr0.execute_with_input(image, input_data)

# 3. Generate a zero-knowledge proof
receipt = pyr0.prove_segment(segments[0])

# 4. Verify the proof
is_valid = receipt.verify()
# or
is_valid = pyr0.verify_receipt(receipt)

# 5. Extract public outputs (journal)
journal = receipt.journal_bytes()
```

## Main Functions

### `load_image_from_elf(elf_bytes: bytes) -> Image`
Loads a RISC Zero program from ELF binary data.
- **Input**: Raw bytes of a compiled RISC Zero guest program
- **Returns**: An `Image` object representing the loaded program

### `execute_with_input(image: Image, input: bytes, segment_size_limit: Optional[int] = None) -> Tuple[List[Segment], SessionInfo]`
Executes a loaded program with given inputs.
- **image**: The loaded program
- **input**: Input data to provide to the guest program
- **segment_size_limit**: Optional limit on segment size (power of 2)
- **Returns**: Tuple of (segments list, session info)

### `prove_segment(segment: Segment) -> SegmentReceipt`
Generates a zero-knowledge proof for a segment.
- **segment**: A segment from execution
- **Returns**: A receipt containing the proof

### `verify_receipt(receipt: SegmentReceipt) -> None`
Verifies a proof receipt using default verification context.
- **receipt**: The receipt to verify
- **Raises**: RuntimeError if verification fails
- **Note**: This only verifies the cryptographic integrity of the seal. For full verification including exit code and image ID checks, use `Receipt.verify(image_id)`

### `lift_segment_receipt(segment_receipt: SegmentReceipt) -> SuccinctReceipt`
Converts a segment receipt to a more compact succinct receipt.

### `join_segment_receipts(receipts: List[SegmentReceipt]) -> SuccinctReceipt`
Combines multiple segment receipts into a single succinct receipt.

## Classes

### `Image`
Represents a loaded RISC Zero program.
- Created by `load_image_from_elf()`
- Passed to `execute_with_input()`

### `Segment`
Represents a segment of execution.
- Obtained from `execute_with_input()`
- Used to generate proofs with `prove_segment()`

### `SessionInfo`
Information about an execution session.
- **Methods**:
  - `get_exit_code() -> ExitCode`: Get how the program exited
  - Various properties about the execution

### `ExitCode`
Represents how a program exited.
- **Methods**:
  - `is_halted() -> bool`: Normal termination
  - `is_paused() -> bool`: Paused execution
  - `is_session_limit() -> bool`: Hit session limit
  - `is_fault() -> bool`: Execution fault
  - `get_halted_code() -> int`: Get halt code if halted

### `Receipt`
A complete zero-knowledge proof receipt with full verification capabilities.
- **Methods**:
  - `verify(image_id: str) -> None`: Fully verify the receipt including exit code and image ID
  - `journal_bytes() -> bytes`: Get public outputs (journal)
  - `program_id() -> bytes`: Get the program/image ID that was executed
  - `to_bytes() -> bytes`: Serialize for storage/transmission
  - `from_bytes(data: bytes) -> Receipt`: Deserialize from bytes

### `SegmentReceipt`
A segment-level proof receipt (lower-level than Receipt).
- **Methods**:
  - `verify() -> bool`: Basic verification (deprecated, use verify_integrity)
  - `verify_integrity() -> None`: Verify cryptographic integrity of the seal
  - `get_exit_code() -> int`: Get the exit code from the claim
  - `journal_bytes() -> bytes`: Get public outputs
  - `__getstate__()/__setstate__()`: For serialization

### `SuccinctReceipt`
A more compact proof receipt.
- Created by lifting or joining segment receipts
- Used for more efficient proof verification

## Serialization

All receipt types support Python pickle protocol:

```python
# Serialize a receipt
import pickle
receipt_data = pickle.dumps(receipt)

# Deserialize a receipt
receipt = pickle.loads(receipt_data)
```

## Example: Complete Prover/Verifier Flow

```python
# PROVER SIDE
image = pyr0.load_image_from_elf(elf_data)
segments, info = pyr0.execute_with_input(image, private_input)
receipt = pyr0.prove_segment(segments[0])

# Serialize and send to verifier
receipt_bytes = pickle.dumps(receipt)

# VERIFIER SIDE
# Deserialize received receipt
receipt = pickle.loads(receipt_bytes)

# Verify the proof
if receipt.verify():
    journal = receipt.journal_bytes()
    print(f"Proof is valid! Public output: {journal}")
else:
    print("Invalid proof!")
```

## Current Limitations

1. **Journal extraction**: Currently returns empty bytes due to RISC Zero 1.2 API changes
2. **Verification**: Simplified implementation - full verification needs enhancement
3. **GPU acceleration**: Available through RISC Zero but not explicitly exposed

The API is designed to be simple for basic use cases while providing access to advanced features like segment joining and proof lifting for more complex applications.