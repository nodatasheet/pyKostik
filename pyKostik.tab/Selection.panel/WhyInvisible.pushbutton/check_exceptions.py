class ValidationError(Exception):
    pass


class TypeValidationError(ValidationError):
    """Type Validation Error"""

    def __init__(self, message=None, expected=None, provided=None):
        # type: (str, type | tuple[type], type) -> None
        self._message = message
        self._expected = expected
        self._provided = provided

    def __str__(self):
        # type: () -> str
        if self._message is not None:
            return self._message

        message = str()

        expected = self._expected
        if expected is not None:
            if isinstance(expected, tuple):
                names = (obj_type.__name__ for obj_type in expected)
                message += ' expected <' + ' or '.join(names) + '>'
            else:
                message += ' expected <' + expected.__name__ + '>'

        if self._provided is not None:
            message += ' got <' + self._provided.__name__ + '>'

        return message


class ViewError(Exception):
    def __init__(self, view_id=None, msg=None):
        # type: (str, str) -> None
        self._view_id = view_id
        self._msg = msg

    def __str__(self):
        message = str()
        if self._msg is not None:
            message = self._msg

        if self._view_id is not None:
            msg_suffix = ' View id<{}>'.format(self._view_id)
            message += msg_suffix

        return message


class ElementError(Exception):
    def __init__(self, elem_id=None, msg=None):
        # type: (str, str) -> None
        self._elem_id = elem_id
        self._msg = msg

    def __str__(self):
        message = str()
        if self._msg is not None:
            message = self._msg

        if self._elem_id is not None:
            msg_suffix = 'Element id<{}>'.format(self._elem_id)
            message += msg_suffix

        return message


class ElementCategoryError(ElementError):
    pass


class ReportError(Exception):
    pass


class CheckError(Exception):
    pass
