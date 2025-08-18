"""
Guest building functionality for PyR0.
"""

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional


class BuildError(Exception):
    """Base exception for build errors."""
    pass


class GuestBuildFailedError(BuildError):
    """Raised when cargo build command fails."""
    pass


class ElfNotFoundError(BuildError):
    """Raised when ELF file is not found after successful build."""
    pass


class InvalidGuestDirectoryError(BuildError):
    """Raised when guest directory doesn't exist or lacks Cargo.toml."""
    pass


def build_guest(
    guest_dir: str | Path,
    binary_name: Optional[str] = None,
    release: bool = True,
    use_embed_methods: Optional[bool] = None
) -> Path:
    """
    Build a RISC Zero guest program and return the path to the ELF file.
    
    This function handles both build methods:
    1. Standard RISC Zero structure with embed_methods (host/guest setup)
    2. Direct guest build (standalone guest)
    
    Args:
        guest_dir: Path to the guest directory containing Cargo.toml
        binary_name: Name of the binary to build (defaults to package name from Cargo.toml)
        release: If True, build in release mode (recommended)
        use_embed_methods: If True, use standard structure; if False, use direct build;
                          if None, auto-detect based on presence of build.rs in parent
        
    Returns:
        Path to the built ELF file
        
    Raises:
        InvalidGuestDirectoryError: If guest_dir doesn't exist or lacks Cargo.toml
        GuestBuildFailedError: If cargo build command fails
        ElfNotFoundError: If ELF file is not found after successful build
    """
    guest_path = Path(guest_dir).resolve()
    
    # Validate guest directory
    if not guest_path.exists():
        raise InvalidGuestDirectoryError(f"Guest directory does not exist: {guest_path}")
    
    cargo_toml = guest_path / "Cargo.toml"
    if not cargo_toml.exists():
        raise InvalidGuestDirectoryError(f"No Cargo.toml found in guest directory: {guest_path}")
    
    # Determine binary name if not provided
    if binary_name is None:
        # Parse Cargo.toml to get package name or bin name
        import tomllib
        with open(cargo_toml, "rb") as f:
            cargo_data = tomllib.load(f)
        
        # Check for [[bin]] entries first
        if "bin" in cargo_data and cargo_data["bin"]:
            binary_name = cargo_data["bin"][0].get("name")
        
        # Fall back to package name
        if binary_name is None:
            package_name = cargo_data.get("package", {}).get("name")
            if package_name:
                binary_name = package_name.replace("-", "_")
            else:
                raise InvalidGuestDirectoryError(f"Could not determine binary name from {cargo_toml}")
    
    # Auto-detect build method if not specified
    if use_embed_methods is None:
        # Check if parent directory has build.rs with embed_methods
        parent_dir = guest_path.parent
        parent_build_rs = parent_dir / "build.rs"
        
        if parent_build_rs.exists():
            # Check if build.rs contains embed_methods
            with open(parent_build_rs, "r") as f:
                build_content = f.read()
                use_embed_methods = "embed_methods" in build_content
        else:
            use_embed_methods = False
    
    # Calculate expected ELF path based on build method
    if use_embed_methods:
        # Standard RISC Zero structure: target/riscv-guest/<host>/<guest>/riscv32im-risc0-zkvm-elf/release/<binary>
        # We need to find the workspace root and host crate name
        workspace_root = guest_path.parent.parent  # Assuming guest is in <host>/guest/
        host_crate_name = guest_path.parent.name
        guest_crate_name = guest_path.name
        
        # Look for target directory in workspace root or parent directories
        search_dir = guest_path.parent
        while search_dir != search_dir.parent:  # Stop at filesystem root
            potential_target = search_dir / "target" / "riscv-guest"
            if potential_target.exists() or search_dir / "Cargo.lock" in search_dir.iterdir():
                workspace_root = search_dir
                break
            search_dir = search_dir.parent
        
        target_base = workspace_root / "target" / "riscv-guest" / host_crate_name / guest_crate_name
        target_dir = target_base / "riscv32im-risc0-zkvm-elf"
    else:
        # Direct build: <guest_dir>/target/riscv32im-risc0-zkvm-elf/release/<binary>
        target_dir = guest_path / "target" / "riscv32im-risc0-zkvm-elf"
    
    if release:
        elf_path = target_dir / "release" / binary_name
    else:
        elf_path = target_dir / "debug" / binary_name
    
    # Always clean build artifacts to ensure fresh build
    if use_embed_methods:
        # For standard builds, clean from workspace target
        clean_dir = workspace_root / "target" / "riscv-guest"
        if clean_dir.exists():
            shutil.rmtree(clean_dir, ignore_errors=True)
            print(f"Cleaned build cache: {clean_dir}")
    else:
        # For direct builds, run cargo clean in the guest directory
        clean_result = subprocess.run(
            ["cargo", "clean"],
            cwd=guest_path,
            capture_output=True,
            text=True,
            check=False
        )
        if clean_result.returncode == 0:
            print(f"Cleaned build cache for {guest_path.name}")
    
    # Build the guest program
    print(f"Building guest program: {binary_name}")
    print(f"  Directory: {guest_path}")
    print(f"  Build method: {'Standard (embed_methods)' if use_embed_methods else 'Direct'}")
    
    if use_embed_methods:
        # Build from the host directory (parent of guest)
        build_dir = guest_path.parent
        cmd = ["cargo", "build"]
    else:
        # Direct build from guest directory
        build_dir = guest_path
        cmd = [
            "cargo", "+risc0", "build",
            "--target", "riscv32im-risc0-zkvm-elf"
        ]
    
    if release:
        cmd.append("--release")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=build_dir,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = f"Guest build failed with exit code {result.returncode}"
            if result.stderr:
                # Extract relevant error lines
                stderr_lines = result.stderr.strip().split('\n')
                # Show last 10 lines of error
                relevant_errors = '\n'.join(stderr_lines[-10:])
                error_msg += f"\n\nBuild errors:\n{relevant_errors}"
            raise GuestBuildFailedError(error_msg)
            
    except FileNotFoundError:
        raise GuestBuildFailedError("cargo or cargo-risczero not found. Please install RISC Zero toolchain.")
    except subprocess.SubprocessError as e:
        raise GuestBuildFailedError(f"Failed to run cargo build: {e}")
    
    # Verify ELF was created
    if not elf_path.exists():
        # For standard structure, also check without the nested directories in case structure is different
        if use_embed_methods:
            # Try alternative paths
            alt_paths = [
                # Try without host crate name
                workspace_root / "target" / "riscv-guest" / guest_crate_name / "riscv32im-risc0-zkvm-elf" / ("release" if release else "debug") / binary_name,
                # Try with different binary name formats
                elf_path.with_name(binary_name.replace("_", "-")),
                elf_path.with_name(binary_name.replace("-", "_")),
            ]
            
            for alt_path in alt_paths:
                if alt_path.exists():
                    print(f"Found ELF at alternative location: {alt_path}")
                    return alt_path
        
        # Try to provide helpful information about what might have gone wrong
        parent_dir = elf_path.parent
        if not parent_dir.exists():
            # Try to find where files actually got built
            search_patterns = [
                f"**/target/**/riscv32im-risc0-zkvm-elf/**/{binary_name}",
                f"**/target/**/riscv32im-risc0-zkvm-elf/**/{binary_name.replace('_', '-')}",
                f"**/target/**/riscv32im-risc0-zkvm-elf/**/{binary_name.replace('-', '_')}",
            ]
            
            found_elfs = []
            search_root = workspace_root if use_embed_methods else guest_path
            for pattern in search_patterns:
                found_elfs.extend(search_root.glob(pattern))
            
            if found_elfs:
                # Use the first found ELF
                actual_elf = found_elfs[0]
                print(f"Warning: Expected ELF at {elf_path}")
                print(f"         But found at {actual_elf}")
                return actual_elf
            
            raise ElfNotFoundError(
                f"ELF not found at {elf_path}\n"
                f"Target directory doesn't exist: {parent_dir}\n"
                f"Searched in: {search_root}\n"
                f"This suggests the build didn't produce any output."
            )
        
        # List what files ARE in the directory
        existing_files = list(parent_dir.glob("*"))
        if existing_files:
            files_list = "\n  ".join(str(f.name) for f in existing_files[:5])
            raise ElfNotFoundError(
                f"ELF not found at {elf_path}\n"
                f"Files found in {parent_dir}:\n  {files_list}\n"
                f"The binary name might be different than expected: {binary_name}"
            )
        else:
            raise ElfNotFoundError(
                f"ELF not found at {elf_path}\n"
                f"Target directory is empty: {parent_dir}"
            )
    
    print(f"✓ Guest program built successfully: {elf_path}")
    print(f"  Size: {os.path.getsize(elf_path):,} bytes")
    
    return elf_path


