from pykostik.exceptions import PyKostikException


class GeometryException(PyKostikException):
    pass


class InvalidOperationException(GeometryException):
    pass


class ValidationException(GeometryException):
    pass
