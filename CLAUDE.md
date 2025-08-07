# Claude Development Notes

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

## Building for Distribution

To build a wheel for distribution:
```bash
uv tool run maturin build --release
```

To install in development mode (editable install):
```bash
uv tool run maturin develop
```