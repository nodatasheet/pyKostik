from numbers import Number


def almost_eq(a, b, rel_tol=1e-09, abs_tol=0.0):
    # type: (Number, Number, float, float) -> bool
    """
    A function for testing approximate equality of two numbers.
    Same as `math.isclose` since Python v3.5
    https://www.python.org/dev/peps/pep-0485

    Set `abs_tol` to compare with zero.
    """
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
