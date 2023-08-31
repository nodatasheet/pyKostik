"""Abstract Revit Object to represent Revit API types."""
from abc import abstractmethod, abstractproperty


class AbstractRevitObject(object):
    pass


class AbstractRevitCoordinates(AbstractRevitObject):

    @abstractmethod
    def Add(self, other):
        # type: (AbstractRevitCoordinates) -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def AngleTo(self, other):
        # type: (AbstractRevitCoordinates) -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def CrossProduct(self, other):
        # type: (AbstractRevitCoordinates) -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def GetLength(self):
        # type: (AbstractRevitCoordinates) -> float
        pass

    @abstractmethod
    def Divide(self, value):
        # type: (float) -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def DistanceTo(self, other):
        # type: (AbstractRevitCoordinates) -> float
        pass

    @abstractmethod
    def DotProduct(self, other):
        # type: (AbstractRevitCoordinates) -> float
        pass

    @abstractmethod
    def IsAlmostEqualTo(self, other):
        # type: (AbstractRevitCoordinates) -> bool
        pass

    @abstractmethod
    def IsUnitLength(self):
        # type: () -> bool
        pass

    @abstractmethod
    def IsZeroLength(self):
        # type: () -> bool
        pass

    @abstractmethod
    def Multiply(self, value):
        # type: (float) -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def Negate(self):
        # type: () -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def Normalize(self):
        # type: () -> AbstractRevitCoordinates
        pass

    @abstractmethod
    def Subtract(self, other):
        # type: (AbstractRevitCoordinates) -> AbstractRevitCoordinates
        pass

    @abstractproperty
    def Zero(self):
        # type: () -> AbstractRevitCoordinates
        pass


class AbstractRevitUV(AbstractRevitCoordinates):

    @abstractproperty
    def U(self):
        # type: () -> float
        pass

    @abstractproperty
    def V(self):
        # type: () -> float
        pass


class AbstractRevitXYZ(AbstractRevitCoordinates):

    @abstractproperty
    def X(self):
        # type: () -> float
        pass

    @abstractproperty
    def Y(self):
        # type: () -> float
        pass

    @abstractproperty
    def Z(self):
        # type: () -> float
        pass


class AbstractRevitTransform(AbstractRevitObject):
    pass


class AbstractRevitCurve(AbstractRevitObject):

    @abstractmethod
    def ComputeDerivatives(parameter, normalized):
        # type: (float, bool) -> AbstractRevitTransform
        pass
