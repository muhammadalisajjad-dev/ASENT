"""Shared exception hierarchy for ASENT modules."""

from __future__ import annotations


class AsentError(Exception):
    """Base class for all ASENT analyzer errors."""


class HclSyntaxError(AsentError):
    """Raised when Terraform/HCL input cannot be parsed."""

    def __init__(self, message: str, location: object | None = None) -> None:
        self.location = location
        if location is not None:
            message = f"{location}: {message}"
        super().__init__(message)


class UnsupportedTerraformError(AsentError):
    """Raised when input uses Terraform features outside the supported subset."""


class InputError(AsentError):
    """Raised for bad CLI/input paths or malformed input files."""


class ObligationError(AsentError):
    """Raised when the security obligation file is invalid."""


class BaselineValidationError(AsentError):
    """Raised when the trusted baseline does not realize the obligation."""
