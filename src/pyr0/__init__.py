from pyr0._rust import *
from pyr0 import serialization
from typing import Union

# Type alias for better clarity
ProofReceipt = Union['SegmentReceipt', 'SuccinctReceipt']

__all__ = [
    # Core API functions
    "load_image",
    "prove",  # New unified function
    
    # Advanced API (for multi-segment or custom workflows)
    "execute_with_input", 
    "generate_proof",
    "lift_receipt",
    "join_succinct_receipts",
    "join_segment_receipts",
    
    # Modules and classes
    "serialization",
    "Image",
    "Segment",
    "ExitCode",
    "SessionInfo",
    "SegmentReceipt",
    "SuccinctReceipt",
    
    # Type aliases
    "ProofReceipt",
]
