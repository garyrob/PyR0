# PyR0 Proof Composition Guide

## Critical Concepts

### The Three Truths of Composition

1. **The guest NEVER sees receipts** - Only the host handles Receipt objects
2. **env::verify() takes JOURNAL bytes** - Not receipt bytes!  
3. **Succinct proves resolve assumptions** - Composite receipts are conditional

## DO's and DON'Ts

### ✅ DO

| Action | Why | Example |
|--------|-----|---------|
| Use `Composer` API | Type-safe, validates assumptions | `comp = Composer(image)` |
| Generate succinct proofs for composition | Only unconditional receipts can be assumptions | `prove_succinct(image, input)` |
| Pass journal bytes to env::verify | That's what it expects | `env::verify(id, &journal_bytes)` |
| Use preflight checks | Catch errors before expensive proving | `comp.preflight_check()` |
| Verify image IDs match | Ensure receipts are from expected programs | `receipt.matches_image_id(expected)` |
| Use typed writers | Prevents serialization mismatches | `comp.write_u32(value)` |

### ❌ DON'T

| Action | Why It's Wrong | What Happens |
|--------|----------------|--------------|
| Pass receipt bytes to env::verify | It expects journal bytes | Guest will panic or verify wrong data |
| Use composite receipts as assumptions | They have unresolved assumptions | Composition will fail |
| Skip preflight checks | Mismatches cause expensive failures | Waste time on doomed proofs |
| Trust claimed_image_id | It's untrusted data from receipt | Security vulnerability |
| Mix write methods incorrectly | Type mismatches | Guest will read garbage |
| Use fake receipts in production | They're test-only | No actual verification |

## Common Patterns

### Single Composition
```python
# 1. Generate inner proof (must be succinct!)
inner = pyr0.prove_succinct(inner_image, inner_input)

# 2. Set up outer proof with Composer
comp = pyr0.Composer(outer_image)
comp.assume(inner)  # Validates it's unconditional

# 3. Write data for outer guest
comp.write_image_id(inner_image.id)        # 32 bytes
comp.write_slice(inner.journal_bytes)      # Variable length

# 4. Generate composed proof (defaults to succinct)
outer = comp.prove()  # Runs preflight, then proves
```

### Tree Aggregation
```python
# Multiple assumptions in one guest
comp = pyr0.Composer(aggregator_image)
comp.assume_many([left_receipt, right_receipt])  # All must be succinct

# Guest will call env::verify twice
comp.write_image_id(left_image.id)
comp.write_slice(left.journal_bytes)
comp.write_image_id(right_image.id)
comp.write_slice(right.journal_bytes)

# Tell Composer what to expect
comp.expect_verification(left_image.id, left.journal_bytes)
comp.expect_verification(right_image.id, right.journal_bytes)

# Generate aggregated proof
final = comp.prove()  # Resolves both assumptions
```

### Batch Verification
```python
# Use VerifierContext for efficiency
ctx = pyr0.VerifierContext()
for receipt in many_receipts:
    receipt.verify_with_context(trusted_image_id, ctx)
```

## Error Meanings

| Error | Cause | Fix |
|-------|-------|-----|
| "No assumption matches expected verification" | Guest env::verify doesn't match assumptions | Check image_id and journal match |
| "Cannot use composite receipt as assumption" | Trying to assume conditional proof | Use prove_succinct() or compress_to_succinct() |
| "Receipt has unresolved assumptions" | Composite receipt in wrong context | Generate succinct proof |
| "Invalid image ID length" | Not exactly 32 bytes | Use write_image_id() helper |
| "Unused assumption" | Provided assumption but no env::verify | Remove assumption or add verification |

## The Mental Model

```
Host                          Guest
----                          -----
receipt = prove(...)          env::read/write for I/O
                             
comp.assume(receipt)   -->    env::verify(id, journal)
                             (adds assumption, no actual verify)
                             
comp.prove(succinct)   -->    [Recursion program resolves all]
= final_receipt              (Now all assumptions proven!)
```

## Remember

- **Assumptions are lazy** - env::verify doesn't actually verify in-guest
- **Succinct is magic** - It runs the recursion program to resolve everything  
- **Journal ≠ Receipt** - Journal is just the public output bytes
- **Trust nothing claimed** - Always verify with known-good image IDs