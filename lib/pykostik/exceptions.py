

class PyKostikException(Exception):
    """Base class for pyKostik exceptions."""


class InvalidOperationException(PyKostikException):
    """Invalid Operation Exception"""
    pass


class ValidationError(PyKostikException):
    """Base class for Validation Errors"""
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""
    pass
