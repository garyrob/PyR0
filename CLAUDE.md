# Claude Development Notes

## Essential Development Workflow

**After ANY changes to Rust code (src/*.rs):**

```bash
# 1. Build the wheel
uv tool run maturin build --release
# Maturin will output: "📦 Built wheel for CPython 3.12 to /path/to/PyR0-X.X.X-cp312-cp312-platform.whl"

# 2. Force reinstall (CRITICAL - must use --force-reinstall)
# Option A: Use the * wildcard to match the latest built wheel
uv pip install --force-reinstall target/wheels/PyR0-*.whl

# Option B: Copy the exact filename from maturin's output
# Example: uv pip install --force-reinstall target/wheels/PyR0-0.1.0-cp312-cp312-macosx_11_0_arm64.whl
```

**Why --force-reinstall is required:**
- Without it, uv uses cached versions even after rebuilding
- Changes won't take effect without forcing reinstallation
- This is the #1 cause of "changes not working" issues

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

- Use `uv tool run maturin develop` to build the extension
  - NOT `uv run maturin develop` (which tries to find maturin in the environment)
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

To build a wheel for distribution:
```bash
uv tool run maturin build --release
```

To install in development mode (editable install):
```bash
uv tool run maturin develop
```

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
- **Development (fast iteration)**: `uv tool run maturin develop` (builds into source dir)
- **Testing changes**: `uv tool run maturin build --release` → `uv pip install --force-reinstall`
- **Clean build**: `uv sync --no-editable` (rebuilds everything from scratch)

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