# Claude Development Notes

## CRITICAL: Production Readiness Issues to Fix

**These issues MUST be fixed before PyR0 can be considered production-ready:**

### 1. ✅ FIXED: `dry_run` used in production demo
- **Location**: `demo/ed25519_demo.py` line 123
- **Issue**: Used `pyr0.dry_run()` which executes WITHOUT proving (insecure!)
- **Fix Applied**: Replaced with `pyr0.prove()` to generate actual proof
- **Status**: FIXED - Now generates real proofs

### 2. ✅ FIXED: `VerifierContext` was a complete placeholder
- **Location**: `src/verifier.rs` (file removed)
- **Issue**: Just contained `PhantomData`, no actual implementation
- **Fix Applied**: Removed entirely from API
- **Status**: FIXED - Placeholder API removed

### 3. ✅ FIXED: `verify_integrity` documentation was misleading
- **Location**: `src/receipt.rs` line 359-372  
- **Issue**: Method didn't actually verify seal, just checked claim structure
- **Fix Applied**: Updated documentation to clearly state it only validates claim structure
- **Status**: FIXED - Now honest about limitations

### 4. ✅ FIXED: Debug builds removed entirely
- **Location**: `src/pyr0/build.py`
- **Issue**: Accepted `release=False` parameter (100-1000x slower)
- **Fix Applied**: Removed release parameter, always builds in release mode
- **Status**: FIXED - Only release builds supported

### 5. ✅ FIXED: Test comments about "dev mode"
- **Location**: `test/test_real_verification.py` line 91
- **Issue**: Test mentioned "may indicate dev mode" 
- **Fix Applied**: Removed misleading comments
- **Status**: FIXED - No more dev mode references

**ALL CRITICAL ISSUES HAVE BEEN FIXED - PyR0 is now production-ready**

## Essential Development Workflow

**After ANY changes to Rust code (src/*.rs):**

```bash
# 1. Build the wheel
uv tool run maturin build --release
# Maturin will output: "📦 Built wheel for CPython 3.12 to /path/to/PyR0-X.X.X-cp312-cp312-platform.whl"

# 2. Sync dependencies (if any were added/changed)
uv sync

# 3. Install the new PyR0 wheel
uv pip install -U PyR0==0.8.0  # Replace with current version
# This works because pyproject.toml has:
# [tool.uv] package = false (prevents rebuilding)
# [tool.uv.pip] find-links = ["./target/wheels"] (finds our wheel)
```

**Why this workflow works:**
- `package = false` prevents uv from rebuilding PyR0 on every `uv run`
- `find-links` tells uv where to find our built wheels
- `-U` ensures we get the updated wheel, not a cached version
- This is faster and more reliable than force-reinstall

## Using PyO3 with uv - Key Steps

### Setup

- Add maturin as a dev dependency: `uv add --dev maturin` (not `uv add maturin`)
  - This is because maturin is a build tool, not a runtime dependency
- Create proper directory structure:
  - `src/lib.rs` for Rust code
  - `Cargo.toml` for Rust dependencies
  - `pyproject.toml` with maturin build configuration

### PyO3 Version Compatibility

- Use PyO3 0.23.4+ with the new bound-module style
- Module initialization must use: `fn _rust(m: &Bound<'_, PyModule>) -> PyResult<()>`
- Use `PyDict::new(py)` not `PyDict::new_bound(py)` (the latter is deprecated)
- Avoid `///` doc comments - use `//` instead

### Building

- Use `uv tool run maturin build --release` to build the extension
  - NOT `uv run maturin build` (which tries to find maturin in the environment)
  - NOT `uv tool run maturin develop` (debug builds are unusable with RISC Zero)
  - `uv tool run` executes maturin as a standalone tool

### Project Configuration

```toml
# pyproject.toml
[build-system]
requires = ["maturin>=1.7,<2.0"]
build-backend = "maturin"

[tool.maturin]
module-name = "your_module._rust"
features = ["pyo3/extension-module"]
```

### Key Differences from pip

- `uv add` adds to project dependencies
- `uv add --dev` adds to development dependencies
- `uv tool run` runs tools without installing them in the environment
- `uv pip install` would install into the environment (but we don't need this for maturin)

## Running Python Scripts with uv

To run Python scripts in the uv environment:
```bash
# Correct way - uv runs the script directly:
uv run scriptname.py

# NOT this way:
uv run python scriptname.py  # ❌ Wrong
```

## Building for Distribution

**CRITICAL: Always use release builds for PyR0**

```bash
# ALWAYS use this:
uv tool run maturin build --release

# NEVER use this:
uv tool run maturin develop  # ❌ DO NOT USE
```

**Why we don't use `maturin develop`:**

1. **Debug mode performance is catastrophic for RISC Zero:**
   - Proof generation: 100-1000x slower (30 seconds → 8+ hours)
   - Proof verification: 10-100x slower
   - Memory usage: 2-5x higher
   - Debug builds may exhaust memory on large proofs

2. **RISC Zero-specific problems with debug builds:**
   - **Segment execution timeout** - Debug mode is so slow that zkVM segments may timeout
   - **Memory exhaustion** - Unoptimized code uses far more memory, causing OOM errors
   - **Incorrect benchmarks** - Performance tests become meaningless
   - **Missing SIMD optimizations** - Critical cryptographic operations lack vectorization
   - **Stack overflow** - Debug builds have larger stack frames, causing overflows in recursive merkle operations
   - **Test false positives** - Tests may pass in debug but fail in production due to timing/memory differences

3. **Cryptographic operations require release mode:**
   - Field arithmetic operations are 50-100x slower without optimization
   - Poseidon hash computations become bottlenecks
   - SHA-256 merkle tree operations lack hardware acceleration

4. **Debug assertions can hide bugs:**
   - Overflow checks in debug mode prevent wrapping arithmetic
   - Bounds checks that don't exist in release mode
   - Different behavior between debug and release can mask real issues

**The correct workflow is ALWAYS:**
```bash
# Build optimized wheel
uv tool run maturin build --release

# Install it
uv pip install --force-reinstall target/wheels/PyR0-*.whl
```

This ensures consistent, production-ready performance for all RISC Zero operations.

## Important: Editable vs Non-Editable Installs with uv

**Problem**: By default, `uv` installs projects in editable mode, which causes Python to import from the source directory (`src/pyr0/`) instead of the compiled extension module. This leads to:
- Missing attributes like `image_id` on PyO3 classes
- Tests using outdated code even after rebuilding
- Errors like `AttributeError: 'pyr0.Image' object has no attribute 'image_id'`
- New Python modules not found: `ImportError: cannot import name 'serialization'`

**Solution**: After making changes to ANY file (Rust or Python), rebuild and reinstall:

```bash
# ALWAYS DO THIS AFTER MAKING CHANGES:

# Step 1: Build the wheel
uv tool run maturin build --release

# Step 2: Force reinstall (IMPORTANT: use --force-reinstall to override cache)
uv pip install --force-reinstall target/wheels/PyR0-*.whl

# Alternative (slower but automatic):
uv sync --no-editable
```

**Common Issues and Solutions**:

1. **`ImportError: cannot import name 'serialization'`**
   - Cause: New Python module not in installed package
   - Fix: Rebuild and force reinstall (see above)

2. **`AttributeError: 'pyr0.Image' object has no attribute 'image_id'`**
   - Cause: Using old version or editable install
   - Fix: Rebuild and force reinstall (see above)

3. **Changes not taking effect**
   - Cause: Cached wheel or editable install
   - Fix: Use `--force-reinstall` flag

4. **`uv sync --no-editable` seems to do nothing**
   - Cause: No version change detected
   - Fix: Use manual build + install instead

**Debugging Import Issues**:
```python
import pyr0
print(pyr0.__file__)  
# Good: /path/to/.venv/lib/python3.12/site-packages/pyr0/__init__.py
# Bad:  /path/to/project/src/pyr0/__init__.py (editable install)

# Check if new modules are available:
print(dir(pyr0))  # Should show 'serialization' if properly installed
```

**Workflow Summary**:
- **After ANY change**: Build wheel → Force reinstall
- **Testing changes**: `uv tool run maturin build --release` → `uv pip install --force-reinstall`
- **Clean build**: `uv sync --no-editable` (rebuilds everything from scratch)
- **NEVER use**: `uv tool run maturin develop` (debug builds break RISC Zero)

**Note**: The `demo/ed25519_demo.py` script will detect and warn about the editable install issue automatically.

## Version Control Requirements

**CRITICAL**: Version numbers MUST be updated for every push to GitHub.

### Before Every Push:
1. **ASK the user** what the version number should be
2. Update version in THREE places:
   - `pyproject.toml` - the `version = "x.x.x"` line
   - `Cargo.toml` - the `version = "x.x.x"` line  
   - `README.md` - the version badge and any version references
3. Include version in commit message (e.g., "Add feature X (v0.1.0)")
4. Create and push a git tag:
   ```bash
   git tag -a vX.X.X -m "Description of changes"
   git push origin vX.X.X
   ```

### Version Numbering Scheme:
- **0.0.x** - Pre-alpha experimental releases
- **0.x.x** - Alpha/Beta releases
- **1.x.x** - Stable releases (future)

**Remember**: ALWAYS ask "What version number should this be?" before pushing to GitHub.

## Test and Demo Requirements

**CRITICAL**: All tests and demos MUST follow strict error handling guidelines to ensure reliability and maintainability.

### Mandatory Requirements for ALL Tests and Demos:

1. **Exit Codes**: 
   - MUST exit with code 0 on success, 1 on ANY failure
   - MUST track failures throughout execution (e.g., `test_passed = False`)
   - MUST NOT return success if any part failed

2. **No Silent Failures**:
   - NEVER treat missing dependencies as optional or acceptable
   - NEVER use warning symbols (⚠️) for actual failures - use error symbols (✗)
   - NEVER skip tests silently - missing prerequisites are failures
   - NEVER return success when errors occurred but were caught

3. **Exception Handling**:
   - MUST fail the test if an unexpected exception occurs
   - MUST NOT catch and ignore exceptions that indicate real problems
   - MUST NOT continue execution after critical failures

4. **Dependencies**:
   - ALL dependencies (like PyR0, merkle_py) are REQUIRED, not optional
   - If a dependency is missing, the test/demo MUST fail with a clear error
   - NEVER print "install X to enable feature" - if X is needed, its absence is a failure

5. **Validation**:
   - MUST verify ALL expected outcomes, not just print them
   - MUST fail if outputs don't match expectations (wrong size, format, values)
   - MUST check return codes of called functions and demos

### Integration with Master Test Runner:

All new tests and demos MUST be added to `run_all_tests.sh`:

```bash
# Add your test/demo to the appropriate section:
run_test "Your Test Name" "uv run path/to/your_test.py"
```

The master test runner (`./run_all_tests.sh`):
- Runs tests and demos in sequence, aborting immediately on first failure
- Shows colored output with clear failure messages
- Exits with code 1 immediately upon ANY test failure
- Exits with code 0 only if ALL tests pass (zero tolerance)
- Does NOT skip tests for missing dependencies - all are required

### Example of CORRECT Test Structure:

```python
#!/usr/bin/env python3
import sys

test_passed = True

try:
    # Test something
    result = do_something()
    if not result:
        print("✗ Test failed: unexpected result")
        test_passed = False
except Exception as e:
    print(f"✗ Test failed with error: {e}")
    test_passed = False

if test_passed:
    print("✓ All tests passed")
    sys.exit(0)
else:
    print("✗ Some tests failed")
    sys.exit(1)
```

### Example of INCORRECT Patterns (NEVER DO THESE):

```python
# WRONG - Silent failure
try:
    import required_module
except ImportError:
    print("⚠️ Module not available, skipping test")  # NO!
    return  # This hides a failure!

# WRONG - Treating errors as acceptable
if not dependency_exists:
    print("Continuing without dependency...")  # NO!
    # Should fail here instead

# WRONG - Success despite errors
except Exception as e:
    print(f"Error: {e}")
    # No test_passed = False here!  # NO!
```

**Remember**: The goal is ZERO TOLERANCE for failures. If something should work, it MUST work, or the test MUST fail visibly with exit code 1.