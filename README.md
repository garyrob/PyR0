## PyR0 - Python wrapper for RISC Zero prover

<img src="https://github.com/l2iterative/r0prover-python/raw/main/title.png" align="right" style="margin: 20px;" alt="many military tanks rolling in parallel on the desert" width="300"/>

When people talk about accelerating zero-knowledge proofs, there are usually two approaches:
- hardware acceleration
- distributed computation

After years of exploration, many in the industry (including Supranational, Ingonyama) would agree that Nvidia GPU and 
Apple Metal GPU seems to be doing pretty well for hardware acceleration. FPGA and ASIC are still too early to compete, 
and evidence in chip design suggests that FPGA/ASIC are **unlikely** to beat GPU eventually—any idea that can challenge this assertion 
is most welcomed. In fact, [Omer Shlomovits](https://www.omershlomovits.com/) from [Ingonyama](https://www.ingonyama.com/) 
and I have a bounty for breakthrough ideas in hardware acceleration.

This leaves distributed computing. 

The idea is that, if we have a zero-knowledge proof task, we want to distribute it to multiple machines and then aggregate 
their work together. This would require a zero-knowledge proof system that is **distributed-computation-friendly**.
- the different machines involving in the process are **laconic** and **taciturn**, i.e., they have **minimalistic** communication between each other.
- the individual proof work can be merged in an efficient way without severely sacrificing the overall proof generation time

This idea has, however, been systematically studied. 

- [zkBridge](https://dl.acm.org/doi/10.1145/3548606.3560652) (ACM CCS 2022), which leads to our portfolio company 
[Polyhedra](https://polyhedra.network/), discovers that an algebraic holographic proof protocol, [Goldwasser-Kalai-Rothblum (GKR)](https://people.cs.georgetown.edu/jthaler/GKRNote.pdf), 
can be made distributed-computation-friendly by having each machine handle part of the multilinear extensions. 
   * However, committing the input polynomials (through FRI) still has to be done in a federated manner, which is only suitable 
for circuits with small inputs. 
- [Pianist](https://www.computer.org/csdl/proceedings-article/sp/2024/313000a035/1RjEaaM09eU) (IEEE S&P 2024) shows that, 
by using [bivariate KZG commitment](https://eprint.iacr.org/2011/587.pdf), one can make polynomial commitment 
distributed-computation-friendly, coupled with Plonk (or its variants), which are distributed-computation-friendly, 
one can create fully distributed-computation-friendly proof systems. 
   * However, it requires homomorphic polynomial commitments, for which KZG is but not FRI. But KZG is usually slower.
- all SNARK protocols can be made distributed-computation-friendly through [recursive composition](https://people.eecs.berkeley.edu/~alexch/#show-abstract). 
This would incur additional overhead and latency in composing proofs together, but it is a very general approach that 
applies to, technically, any SNARK. 

RISC Zero takes the third approach. The problem with the first two approaches is the same—not working well with FRI, which
still has a prevailing advantage in terms of performance, and the benefit declines if subsequent recursive composition is not avoidable.
For RISC Zero, it is desirable, for Bonsai, to merge proofs from different transactions to lower the on-chain verification 
costs, which means that all proofs would eventually go through recursion, which discourages KZG-based approach.

The third approach reduces the entire acceleration task into a simple step: **coordinate** enough machines to work together.
Tools for this purpose have been extensively studied in machine learning, and we here focus on the [Dask](https://www.dask.org/) 
framework.

We have experimented with the [Ray](https://github.com/ray-project/ray), but the fact that it uses `fork()` appears to 
require a lot of care when handling with the CUDA connections. 

### Background in Dask, a distributed computing framework

[Dask](https://www.dask.org/) is another distributed computing framework with wide adoption. It can be done in a similar manner.

<img src="https://docs.dask.org/en/stable/_images/dask_horizontal.svg" align="right" width="200"/>

```python
import pyr0
from dask.distributed import Client, LocalCluster

if __name__ == '__main__':
  cluster = LocalCluster()
  client = Client(cluster)
  
  elf_handle = open("elf", mode="rb")
  elf = elf_handle.read()
  image = pyr0.load_image_from_elf(elf)
  input = bytes([33, 0, 0, 0, ...]) # omit the detail input
  segments, info = pyr0.execute_with_input(image, input)
  
  # distribute the task using `client.submit(func, args)`
  future_1 = client.submit(pyr0.prove_segment, segments[0])
  future_2 = client.submit(pyr0.prove_segment, segments[1])
  
  # obtain the results using `future.result()`
  receipt_1 = future_1.result()
  receipt_2 = future_2.result()
```

### Supported versions

Currently, the library is compiled with CUDA 12.3. There is a risk that it would not work with other versions of CUDA and
would require compilation from the source.

### Development with uv

This project uses [uv](https://docs.astral.sh/uv/) for Python package management and [maturin](https://www.maturin.rs/) for building the Rust extension module.

#### Building and Installing Changes

When you make changes to either Rust code (`src/*.rs`) or Python code (`src/pyr0/*.py`), you need to rebuild and reinstall:

```bash
# Step 1: Build the wheel with your changes
uv tool run maturin build --release

# Step 2: Install the built wheel (force reinstall to override cached version)
uv pip install --force-reinstall target/wheels/PyR0-0.2.0-cp312-cp312-macosx_11_0_arm64.whl

# Alternative: Use uv sync for automatic rebuild (slower, builds from source)
uv sync --no-editable
```

**Note**: The wheel filename includes your Python version and platform. Adjust accordingly:
- `cp312` = CPython 3.12
- `macosx_11_0_arm64` = macOS ARM64 (Apple Silicon)

#### Important: Editable vs Non-Editable Installs

By default, `uv` installs projects in **editable mode**, which means Python imports directly from the source directory (`src/pyr0/`). This can cause issues with PyO3/Rust extensions because:

1. The compiled `.so` file with new Rust features won't be in the source directory
2. You'll see errors like `AttributeError: 'pyr0.Image' object has no attribute 'image_id'`
3. Tests will import outdated code even after rebuilding
4. New Python modules may not be found (e.g., `ImportError: cannot import name 'serialization'`)

**To fix this issue:**

```bash
# Option 1: Build and install manually (faster for repeated builds)
uv tool run maturin build --release
uv pip install --force-reinstall target/wheels/PyR0-0.2.0-*.whl

# Option 2: Let uv handle everything (slower, rebuilds from scratch)
uv sync --no-editable
```

**For development workflows:**

- **Quick iteration (editable)**: Use `uv tool run maturin develop` to build the extension into the source directory
- **Testing changes**: Build wheel + force reinstall (Option 1 above)
- **Clean build**: Use `uv sync --no-editable` (Option 2 above)
- **Release testing**: Create a fresh venv and install the wheel to ensure it works correctly

If you see import errors or missing attributes, check where Python is importing from:
```python
import pyr0
print(pyr0.__file__)  # Should be in site-packages, not src/
```

### License

As mentioned in [pyproject.toml](pyproject.toml), this Python module, listed on PyPI, is under MIT and Apache 2 licenses.
