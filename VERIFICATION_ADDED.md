# Zero-Knowledge Proof Verification Support

This document describes the verification functionality added to r0prover-python.

## What Was Added

### 1. Receipt Verification Methods

Added to `SegmentReceipt` class:
- `journal_bytes()` - Extract the journal (public outputs) from a receipt
- `verify()` - Verify that a receipt contains a valid proof

### 2. Standalone Verification Function

Added to module:
- `verify_receipt(receipt: SegmentReceipt) -> bool` - Verify any receipt

## How It Works

### Generating a Proof (Prover Side)
```python
# Load program
image = pyr0.load_image_from_elf(elf_data)

# Execute with private inputs
segments, info = pyr0.execute_with_input(image, input_data)

# Generate proof
receipt = pyr0.prove_segment(segments[0])

# Serialize for transmission
receipt_bytes = receipt.__getstate__()
```

### Verifying a Proof (Verifier Side)
```python
# Deserialize received receipt
receipt = pyr0.SegmentReceipt()
receipt.__setstate__(receipt_bytes)

# Verify the proof
is_valid = receipt.verify()
# or
is_valid = pyr0.verify_receipt(receipt)

# Extract public outputs
journal = receipt.journal_bytes()
```

## Key Changes Made

1. **Updated to Official RISC Zero** - Switched from l2iterative fork to official RISC Zero 1.2
2. **Added Verification API** - Both as method and standalone function
3. **Journal Access** - Can extract public outputs from receipts
4. **Full Prover/Verifier Separation** - Receipts can be serialized, transmitted, and verified independently

## Use Cases

This enables:
- **Proof sharing** - Generate proof on one machine, verify on another
- **Proof storage** - Save proofs for later verification
- **API services** - Build services that verify proofs from clients
- **Privacy-preserving verification** - Verify computations without seeing private inputs

## Example

See `examples/verify_proof.py` for a complete example using Ed25519 signature verification.