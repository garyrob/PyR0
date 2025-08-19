"""Type stubs for PyR0 package."""

from typing import Union, Optional, List, Tuple, overload, Literal
from pathlib import Path

# Re-export from _rust
from pyr0._rust import (
    # Classes
    Image as Image,
    Receipt as Receipt,
    Claim as Claim,
    Composer as Composer,
    SessionInfo as SessionInfo,
    ExitStatus as ExitStatus,
    ExitCode as ExitCode,
    
    # Enums
    ReceiptKind as ReceiptKind,
    ExitKind as ExitKind,
    
    # Functions
    load_image as load_image,
    prove as prove,
    prove_with_opts as prove_with_opts,
    compute_image_id_hex as compute_image_id_hex,
    compress_to_succinct as compress_to_succinct,
    dry_run as dry_run,
)

# From build module
from pyr0.build import (
    build_guest as build_guest,
    BuildError as BuildError,
    GuestBuildFailedError as GuestBuildFailedError,
    ElfNotFoundError as ElfNotFoundError,
    InvalidGuestDirectoryError as InvalidGuestDirectoryError,
)

# Serialization module
from pyr0 import serialization as serialization

__all__: List[str]