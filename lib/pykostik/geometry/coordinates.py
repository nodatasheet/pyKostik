"""Coordinates representing a vector or a point."""

from abc import ABCMeta

from entities import GeometryEntity
from utils import are_numbers_close
from revit_abstracts import AbstractRevitCoordinates

from Autodesk.Revit import DB


class Coordinates(GeometryEntity):
    """Base class for coordinates representing a vector or a point."""

    __metaclass__ = ABCMeta

    _coordinates = tuple()
    _rvt_obj = None  # type: AbstractRevitCoordinates
    revit_type = None

    def __new__(cls, *args, **kwargs):
        if cls is Coordinates:
            raise NotImplementedError(
                'Creating instances of Base class is not allowed.'
            )
        return super(Coordinates, cls).__new__(cls)

    def __str__(self):
        return self.__class__.__name__ + str(self._coordinates)

    def __abs__(self):
        """Returns the distance between these coordinates and the origin."""
        return self.distance_to(self.origin)

    def __contains__(self, item):
        return item in self._coordinates

    def __getitem__(self, key):
        return self._coordinates[key]

    def __iter__(self):
        return self._coordinates.__iter__()

    def __len__(self):
        return len(self._coordinates)

    def __mul__(self, factor):
        return self._wrap(
            self.multiply(factor)
        )

    def __rmul__(self, factor):
        return self.__mul__(factor)

    def __neg__(self):
        return self.negate()

    def __add__(self, other):
        # type: (Coordinates) -> Coordinates
        return self.add(other)

    def __sub__(self, other):
        # type: (Coordinates) -> Coordinates
        return self.substract(other)

    def __lt__(self, other):
        # type: (Coordinates) -> bool
        raise NotImplementedError()

    def __eq__(self, other):
        # type: (Coordinates) -> bool
        """Check coordinates equality using `almost_equal_to()` method
        with the default Revit tolerance.

        For more precise equality, use `almost_equal_to()`
        with specified tolerance.
        """
        return self.almost_equal_to(other)

    def __ne__(self, other):
        # type: (Coordinates) -> bool
        return not self.__eq__(other)

    def __gt__(self, other):
        # type: (Coordinates) -> bool
        return not self.__lt__(other) and self.__ne__(other)

    def __le__(self, other):
        # type: (Coordinates) -> bool
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        # type: (Coordinates) -> bool
        return not self.__lt__(other)

    def almost_equal_to(self, other, tolerance=None):
        # type: (Coordinates, float) -> bool
        """Checks whether these coordinates and other coordinates are the same
        withing a specified tolerance.

        If no tolerance specified, used Revit default tolerance
        of coordinates comparison.
        """
        if tolerance is not None:
            return self._rvt_obj.IsAlmostEqualTo(other._rvt_obj, tolerance)
        return self._rvt_obj.IsAlmostEqualTo(other._rvt_obj)

    def distance_to(self, other):
        # type: (Coordinates) -> float
        """Returns the distance from these coordinates
        to the specified coordinates.
        """
        return self._rvt_obj.DistanceTo(other._rvt_obj)

    def dot_product(self, other):
        # type: (Coordinates) -> float
        """The dot product of vector with these coordinates
        and the vector of other coordinates."""
        return self._rvt_obj.DotProduct(other._rvt_obj)

    def cross_product(self, other):
        # type: (Coordinates) -> Coordinates
        """The cross product of vector with these coordinates
        and the vector of other coordinates."""
        return self._wrap(
            self._rvt_obj.CrossProduct(other._rvt_obj)
        )

    def add(self, other):
        # type: (Coordinates) -> Coordinates
        """Adds other coordinates to self."""
        return self._wrap(
            self._rvt_obj.Add(other._rvt_obj)
        )

    def substract(self, other):
        # type: (Coordinates) -> Coordinates
        """Subtracts other coordinates from self."""
        return self._wrap(
            self._rvt_obj.Subtract(other._rvt_obj)
        )

    def multiply(self, other):
        # type: (float) -> Coordinates
        """Multiples coordinates by a factor."""
        return self._wrap(
            self._rvt_obj.Multiply(other._rvt_obj)
        )

    def negate(self):
        """Negates the coordinates."""
        return self._wrap(
            self._rvt_obj.Negate()
        )

    def _wrap(self, rvt_obj):
        # type: (AbstractRevitCoordinates) -> Coordinates
        """Wraps Revit object to self."""
        return self.__class__(rvt_obj)

    @property
    def coordinates(self):
        # type: () -> tuple[float]
        return self._coordinates

    @property
    def revit_object(self):
        """Gets the revit object which stands behind this wrap."""
        return self._rvt_obj

    @property
    def origin(self):
        """Zero coordinates."""
        return self._wrap(self._rvt_obj.Zero)

    @property
    def is_zero_length(self):
        # type: () -> bool
        """True if every coordinate is zero within Revit tolerance."""
        return self._rvt_obj.IsZeroLength()


class Coordinates2D(Coordinates):
    """Coordinates representing a vector or a point in a 2-dimensional space.
    """

    def __init__(self, revit_uv):
        # type: (DB.UV) -> None
        self._rvt_obj = revit_uv
        self._coordinates = (self._rvt_obj.U,
                             self._rvt_obj.V)

    def __lt__(self, other):
        # type: (Coordinates) -> bool
        """Are these coordinates smaller than other.

        Using lexicographic ordering:
        https://math.stackexchange.com/a/54657

        p1.x < p2.x

        or p1.x = p2.x and p1.y < p2.y

        Equality is approximate.
        """
        self._validate_type(other, type(self))

        if self.x < other.x:
            return True

        if are_numbers_close(self.x, other.x) and self.y < other.y:
            return True

        return False

    @property
    def x(self):
        # type: () -> float
        return self._rvt_obj.U

    @property
    def y(self):
        # type: () -> float
        return self._rvt_obj.V


class Coordinates3D(Coordinates):
    """Coordinates representing a vector or a point in a 3-dimensional space.
    """

    def __init__(self, revit_xyz):
        # type: (DB.XYZ) -> None
        self._rvt_obj = revit_xyz
        self._coordinates = (self._rvt_obj.X,
                             self._rvt_obj.Y,
                             self._rvt_obj.Z)

    def __lt__(self, other):
        # type: (Coordinates) -> bool
        """Are these coordinates smaller than other.

        Using lexicographic ordering:
        https://math.stackexchange.com/a/54657

        p1.x < p2.x

        or p1.x = p2.x and p1.y = p2.y

        or p1.x = p2.x and p1.y = p2.y and p1.z < p2.z

        Equality is approximate.
        """
        self._validate_type(other, type(self))

        if self.x < other.x:
            return True

        if are_numbers_close(self.x, other.x):
            if self.y < other.y:
                return True

            if self.z < other.z and are_numbers_close(self.y, other.y):
                return True

        return False

    @property
    def x(self):
        # type: () -> float
        return self._rvt_obj.X

    @property
    def y(self):
        # type: () -> float
        return self._rvt_obj.Y

    @property
    def z(self):
        # type: () -> float
        return self._rvt_obj.Z
