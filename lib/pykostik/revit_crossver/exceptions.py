

class ValidationException(Exception):
    pass


class TypeValidationException(ValidationException):

    def __init__(self, message=None, expected_type=None, provided_type=None):
        # type: (str, type, type) -> None
        self._message = message
        self._expected_type = expected_type
        self._provided_type = provided_type

    def __str__(self):
        # type: () -> str
        message = str()
        if self._message is not None:
            message = self._message

        if self._expected_type is not None:
            expected_type_name = self._expected_type.__name__
            message += ' expected: ' + expected_type_name + '.'

        if self._provided_type is not None:
            provided_type_name = self._provided_type.__name__
            message += ' got: ' + provided_type_name + '.'

        return message
