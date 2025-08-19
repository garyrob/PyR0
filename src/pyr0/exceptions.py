"""
Custom exception hierarchy for PyR0.

These exceptions provide more specific error handling for different
failure modes in zero-knowledge proof operations.
"""


class PyR0Error(Exception):
    """Base exception for all PyR0 errors."""
    pass


class CompositionError(PyR0Error):
    """
    Raised when proof composition fails.
    
    This typically indicates:
    - Claim mismatch between guest env::verify() and provided assumptions
    - Missing or incorrect assumptions
    - Invalid assumption receipts (composite/fake/failed)
    """
    pass


class VerificationError(PyR0Error):
    """
    Raised when proof verification fails.
    
    This indicates:
    - Invalid cryptographic proof
    - Image ID mismatch
    - Failed execution (non-zero exit code)
    - Corrupted receipt data
    """
    pass


class SerializationError(PyR0Error):
    """
    Raised when serialization/deserialization fails.
    
    This indicates:
    - Size mismatches (e.g., expected 32 bytes, got different)
    - Invalid format for the expected type
    - Corrupted serialized data
    """
    pass


class PreflightError(CompositionError):
    """
    Raised when preflight checks fail before proving.
    
    This indicates composition setup issues that would cause
    proof generation to fail. Catching these early saves time.
    """
    def __init__(self, message: str, issues: list[str]):
        super().__init__(message)
        self.issues = issues


class AssumptionError(CompositionError):
    """
    Raised when assumption validation fails.
    
    This indicates:
    - Trying to use a composite receipt as assumption
    - Using a fake receipt in production
    - Using a failed receipt (non-zero exit)
    """
    pass