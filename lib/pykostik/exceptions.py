

class PyKostikException(Exception):
    """Base class for pyKostik exceptions."""


class FailedAttempt(PyKostikException):
    """Failed Attempt Exception"""
    pass


class InvalidOperationException(PyKostikException):
    """Invalid Operation Exception"""
    pass


class ValidationError(PyKostikException):
    """Base class for Validation Errors"""
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""
    pass
