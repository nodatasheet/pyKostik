import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit import Creation as CRE
from Autodesk.Revit.DB import Structure as STR
# import ItemFactoryBase, Document

from pykostik.wrappers import BasePKWrapper, BasePKObject
from pykostik.wrappers import db

from math import pi


class FamilyInstanceCreationOption(BasePKObject):
    def __init__(self):
        # type: () -> None
        self._inputs = []

    def by_point_symbol_lvl(self, point, symbol, level, str_type=None):
        # type: (db.PkXYZ, db.PkFamilySymbol, db.PkLevel, STR.StructuralType) -> None  # noqa
        """
        Inserts a new instance of a family into the document,
        using a location, type/symbol, and the level.
        """
        if str_type is None:
            str_type = STR.StructuralType.NonStructural

        for attr in point.unwrap, symbol.unwrap, level.unwrap, str_type:
            self._inputs.append(attr)

    @property
    def inputs(self):
        return tuple(self._inputs)


class PkItemFactoryBase(BasePKWrapper):
    _RVT_TYPE = CRE.ItemFactoryBase

    def __init__(self):
        # type: () -> None
        self._rvt_obj = None  # type: CRE.ItemFactoryBase
        raise NotImplementedError(
            'Initialization of {} class is not allowed.'
            .format(self.__class__.__name__)
        )

    def new_model_curve(self, curve, scketch_plane):
        # type: (db.PkCurve, db.PkSketchPlane) -> db.PkModelCurve
        rvt_model_curve = self._rvt_obj.NewModelCurve(
            curve.unwrap,
            scketch_plane.unwrap
        )
        return db.PkModelCurve.wrap(rvt_model_curve)

    def new_detail_curve(self, view, curve):
        # type: (db.PkView, db.PkCurve) -> db.PkDetailCurve
        rvt_det_curve = self._rvt_obj.NewDetailCurve(
            view.unwrap,
            curve.unwrap
        )
        return db.PkDetailCurve(rvt_det_curve)

    def new_detail_circle(self, view, center, diameter):
        # type: (db.PkView, db.PkXYZ, float) -> db.PkDetailArc
        plane = db.PkPlane.new_by_normal_and_origin(
            view.view_direction, center
        )

        circle = db.PkArc.by_plane_radius_angles(
            plane, diameter / 2, 0, 2 * pi
        )

        return self.new_detail_curve(view, circle)

    def new_family_instance(self, family_creation_options):
        # type: (FamilyInstanceCreationOption) -> db.PkFamilyInstance
        options = family_creation_options.inputs
        rvt_fam_instance = self._rvt_obj.NewFamilyInstance(*options)
        return db.PkFamilyInstance.wrap(rvt_fam_instance)


class PkDocumentCreation(PkItemFactoryBase):
    _RVT_TYPE = CRE.Document

    def __init__(self, rvt_obj):
        # type: (CRE.Document) -> None
        self._validate_type(rvt_obj, CRE.Document)
        self._rvt_obj = rvt_obj

    @property
    def unwrap(self):
        return self._rvt_obj


class PkFamilyItemFactory(PkItemFactoryBase):
    _RVT_TYPE = CRE.FamilyItemFactory

    def __init__(self, rvt_obj):
        # type: (CRE.FamilyItemFactory) -> None
        self._validate_type(rvt_obj, CRE.FamilyItemFactory)
        self._rvt_obj = rvt_obj

    @property
    def unwrap(self):
        return self._rvt_obj
