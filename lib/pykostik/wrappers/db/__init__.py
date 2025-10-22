import itertools
import uuid
import clr

from operator import itemgetter
from System import Guid, Int64
from System.Collections.Generic import List

from Autodesk.Revit import DB

from pykostik.wrappers import BasePKObject, BasePKWrapper, creation
from pykostik.wrappers import ui
from pykostik.utils import mathematic as math_utils
from pykostik.utils import iterables as pki
from pykostik import exceptions as pke

try:
    # for type hints
    from typing import Iterable, Iterator, Generator, Self, TypeVar

    T = TypeVar('T')

except ImportError:
    pass


class PkDocument(BasePKWrapper):
    _RVT_TYPE = DB.Document

    def __init__(self, rvt_obj):
        # type: (DB.Document) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Document

    def __eq__(self, other):
        # type: (PkDocument) -> bool
        return type(self) is type(other) \
            and self._rvt_obj.Equals(other._rvt_obj)

    def __ne__(self, other):
        # type: (PkDocument) -> bool
        return not self.__eq__(other)

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def active_view(self):
        # type: () -> PkView
        return PkView.wrap(self._rvt_obj.ActiveView)

    @property
    def create(self):
        return creation.PkDocumentCreation(self._rvt_obj.Create)

    @property
    def fmaily_create(self):
        return creation.PkFamilyItemFactory(self._rvt_obj.FamilyCreate)

    @property
    def is_family_document(self):
        # type: () -> bool
        return self._rvt_obj.IsFamilyDocument

    @property
    def fmaily_manager(self):
        return PkFamilyManager(self._rvt_obj.FamilyManager)

    @property
    def owner_family(self):
        self._validate_family_doc()
        return PkFamily(self._rvt_obj.OwnerFamily)

    def get_element(self, pk_obj):
        # type: (PkElementId | PkReference) -> PkElement
        self._validate_type(pk_obj, tuple([PkElementId, PkReference]))
        rvt_elem = self._rvt_obj.GetElement(pk_obj.unwrap)
        return PkElement.wrap(rvt_elem)

    def regenerate(self):
        return self._rvt_obj.Regenerate()

    def delete(self, id_or_ids):
        # type: (PkElementId | Iterable[PkElementId]) -> list[PkElementId]
        ids_to_delete = List[DB.ElementId]()

        if hasattr(id_or_ids, '__iter__'):
            for id in id_or_ids:
                ids_to_delete.Add(id.unwrap)

        else:
            ids_to_delete.Add(id_or_ids.unwrap)

        deleted_rvt_ids = self._rvt_obj.Delete(ids_to_delete)
        return [PkElementId(id) for id in deleted_rvt_ids]

    def get_default_element_type_id(self, elem_type_grp):
        # type: (DB.ElementTypeGroup) -> PkElementId
        rvt_id = self._rvt_obj.GetDefaultElementTypeId(elem_type_grp)
        return PkElementId(rvt_id)

    def set_default_element_type_id(self, elem_type_grp, type_id):
        # type: (DB.ElementTypeGroup, PkElementId) -> None
        self._rvt_obj.SetDefaultElementTypeId(elem_type_grp, type_id.unwrap)

    def get_family_size_table_manager(self):
        self._validate_family_doc()
        return PkFamilySizeTableManager.get_family_size_table_manager(
            self,
            self.owner_family.id
        )

    def _validate_family_doc(self):
        if not self.is_family_document:
            raise pke.InvalidOperationException(
                '{} is not a family document'.format(self)
            )


class PkFamilyManager(BasePKWrapper):
    _RVT_TYPE = DB.FamilyManager

    def __init__(self, rvt_obj):
        # type: (DB.FamilyManager) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.FamilyManager

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def types(self):
        return [PkFamilyType(t) for t in self._rvt_obj.Types]

    @property
    def current_type(self):
        rvt_type = self._rvt_obj.CurrentType
        if rvt_type is not None:
            return PkFamilyType(rvt_type)

    @current_type.setter
    def current_type(self, value):
        # type: (PkFamilyType) -> None
        self._rvt_obj.CurrentType = value.unwrap

    def rename_current_type(self, name):
        # type: (str) -> None
        self._rvt_obj.RenameCurrentType(name)


class PkFamilyType(BasePKWrapper):
    _RVT_TYPE = DB.FamilyType

    def __init__(self, rvt_obj):
        # type: (DB.FamilyType) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.FamilyType

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def name(self):
        # type: () -> str
        return self._rvt_obj.Name


class PkFamilySizeTableManager(BasePKWrapper):
    _RVT_TYPE = DB.FamilySizeTableManager

    def __init__(self, rvt_obj):
        # type: (DB.FamilySizeTableManager) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.FamilySizeTableManager

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def create_family_size_table_manager(cls, pk_doc, family_id):
        # type: (PkDocument, PkElementId) -> bool
        return DB.FamilySizeTableManager.CreateFamilySizeTableManager(
            pk_doc.unwrap,
            family_id.unwrap
        )

    @classmethod
    def get_family_size_table_manager(cls, pk_doc, family_id):
        # type: (PkDocument, PkElementId) -> Self | None
        rvt_man = DB.FamilySizeTableManager.GetFamilySizeTableManager(
            pk_doc.unwrap,
            family_id.unwrap
        )

        if rvt_man is not None:
            return cls(rvt_man)

    def get_all_size_table_names(self):
        # type: () -> list[str]
        return [tn for tn in self._rvt_obj.GetAllSizeTableNames()]

    def export_size_table(self, table_name, file_path):
        # type: (str, str) -> bool
        return self._rvt_obj.ExportSizeTable(table_name, file_path)


class PkOptions(BasePKWrapper):
    _RVT_TYPE = DB.Options

    def __init__(self, rvt_obj):
        # type: (DB.Options) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Options

    @property
    def unwrap(self):
        return self._rvt_obj


class PkElement(BasePKWrapper):
    _RVT_TYPE = DB.Element

    def __init__(self, elem):
        # type: (DB.Element) -> None
        self._validate_type(elem, self._RVT_TYPE)
        self._rvt_obj = elem  # type: DB.Element

    @property
    def unwrap(self):
        return self._rvt_obj

    def __str__(self):
        return (
            self.__class__.__name__
            + '[rvt_type <'
            + type(self._rvt_obj).__name__
            + '> (id: '
            + str(self.id.value)
            + ')]'
        )

    def __eq__(self, other):
        # type: (PkElement) -> bool
        return self.doc == other.doc and self.id == other.id

    def __ne__(self, other):
        # type: (PkElement) -> bool
        return not self.__eq__(other)

    @property
    def rvt_doc(self):
        return self._rvt_obj.Document

    @property
    def doc(self):
        return PkDocument(self._rvt_obj.Document)

    @property
    def name(self):
        # type: () -> str | None
        return self._rvt_obj.Name

    @property
    def owner_view(self):
        # type: () -> PkView | None
        rvt_view_id = self._rvt_obj.OwnerViewId
        if rvt_view_id is not None:
            return PkElementId(rvt_view_id).get_element(self.doc)

    def get_geometry_element(self, options=None):
        # type: (PkOptions) -> PkGeometryElement
        """Default options: medium detail, no references and no view"""

        if options is None:
            options = PkOptions(DB.Options())
        rvt_geom_elem = self._rvt_obj.get_Geometry(options.unwrap)
        if rvt_geom_elem is not None:
            return PkGeometryElement(rvt_geom_elem)

    def get_rvt_geometry_element(self, options=None):
        # type: (DB.Options) -> DB.GeometryElement
        if options is None:
            options = DB.Options()
        return self._rvt_obj.get_Geometry(options)

    @property
    def id(self):
        return PkElementId(self._rvt_obj.Id)

    @property
    def rvt_id(self):
        return self._rvt_obj.Id

    @property
    def category(self):
        rvt_cat = self._rvt_obj.Category
        if rvt_cat is not None:
            return PkCategory(rvt_cat)

    @property
    def is_grouped(self):
        return self.get_group() is not None

    @property
    def location(self):
        # type: () -> PkLocation | None
        rvt_loc = self._rvt_obj.Location
        if rvt_loc is not None:
            return PkLocation.wrap(rvt_loc)

    @property
    def family_type(self):
        # type: () -> PkFamilySymbol
        param = self.get_parameter(DB.BuiltInParameter.ELEM_FAMILY_PARAM)
        if param is not None:
            return param.as_element_id.get_element(self.doc)

    @family_type.setter
    def family_type(self, new_type):
        # type: (PkFamilySymbol) -> None
        BIP = DB.BuiltInParameter.ELEM_FAMILY_PARAM
        param = self.get_parameter(BIP)

        if param is None:
            raise pke.ParameterNotFoundError(
                'element <{}> does not have parameter {BIP}'
            )

        param.value = new_type.id

    def lookup_param(self, name):
        # type: (str) -> PkParameter | None
        self._validate_type(name, str)
        param = self._rvt_obj.LookupParameter(name)
        if param is not None:
            return PkParameter(param)

    def get_parameter(self, built_in_param):
        # type: (DB.BuiltInParameter) -> PkParameter | None
        self._validate_type(built_in_param, DB.BuiltInParameter)
        param = self._rvt_obj.get_Parameter(built_in_param)
        if param is not None:
            return PkParameter(param)

    def get_bb(self, pk_view=None):
        # type: (PkView) -> PkBoundingBoxXYZ
        rvt_view = None
        if pk_view is not None:
            rvt_view = pk_view.unwrap

        bb = self._rvt_obj.get_BoundingBox(rvt_view)
        if bb is None:
            raise pke.BoundingBoxNotFoundError(
                'Failed getting bounding box from elem {}.'
                .format(self)
            )

        return PkBoundingBoxXYZ(bb)

    def get_elem_type(self):
        type_id = self._rvt_obj.GetTypeId()

        if type_id is None or type_id == DB.ElementId.InvalidElementId:
            return None

        rvt_elem_type = self.rvt_doc.GetElement(type_id)
        if rvt_elem_type is None:
            return None

        return PkElementType.wrap(rvt_elem_type)

    def get_group(self):
        # type: () -> PkGroup
        group_id = self._rvt_obj.GroupId
        if group_id is not None and group_id != DB.ElementId.InvalidElementId:
            return PkGroup(self.rvt_doc.GetElement(group_id))

    def get_type_id(self):
        rvt_id = self._rvt_obj.GetTypeId()
        return PkElementId(rvt_id)

    @property
    def level_id(self):
        rvt_id = self._rvt_obj.LevelId
        if rvt_id is not None:
            return PkElementId(rvt_id)

    @property
    def level(self):
        # type: () -> PkLevel | None
        level_id = self.level_id
        if level_id is not None:
            return level_id.get_element(self.doc)

    def get_valid_type_ids(self):
        # type: () -> list[PkElementId]
        return [PkElementId(eid) for eid in self._rvt_obj.GetValidTypes()]

    def get_valid_types(self):
        return [eid.get_element(self.doc) for eid in self.get_valid_type_ids()]


class PkViewCropRegionShapeManager(BasePKWrapper):
    _RVT_TYPE = DB.ViewCropRegionShapeManager

    def __init__(self, rvt_obj):
        # type: (DB.ViewCropRegionShapeManager) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ViewCropRegionShapeManager

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_crop_shape(self):
        return [PkCurveLoop(cl) for cl in self._rvt_obj.GetCropShape()]

    def set_crop_shape(self, curve_loop):
        # type: (PkCurveLoop) -> None
        return self._rvt_obj.SetCropShape(curve_loop.unwrap)

    @property
    def bottom_anno_crop_offset(self):
        # type: () -> float
        return self._rvt_obj.BottomAnnotationCropOffset

    @bottom_anno_crop_offset.setter
    def bottom_anno_crop_offset(self, value):
        # type: (float) -> None
        """minimal value is 1/96 ft"""
        self._rvt_obj.BottomAnnotationCropOffset = value

    @property
    def top_anno_crop_offset(self):
        # type: () -> float
        return self._rvt_obj.TopAnnotationCropOffset

    @top_anno_crop_offset.setter
    def top_anno_crop_offset(self, value):
        # type: (float) -> None
        """minimal value is 1/96 ft"""
        self._rvt_obj.TopAnnotationCropOffset = value

    @property
    def left_anno_crop_offset(self):
        # type: () -> float
        return self._rvt_obj.LeftAnnotationCropOffset

    @left_anno_crop_offset.setter
    def left_anno_crop_offset(self, value):
        # type: (float) -> None
        """minimal value is 1/96 ft"""
        self._rvt_obj.LeftAnnotationCropOffset = value

    @property
    def right_anno_crop_offset(self):
        # type: () -> float
        return self._rvt_obj.RightAnnotationCropOffset

    @right_anno_crop_offset.setter
    def right_anno_crop_offset(self, value):
        # type: (float) -> None
        """minimal value is 1/96 ft"""
        self._rvt_obj.RightAnnotationCropOffset = value


class PkFamily(PkElement):
    _RVT_TYPE = DB.Family

    def __init__(self, rvt_obj):
        # type: (DB.Family) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Family

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def family_category(self):
        rvt_cat = self._rvt_obj.FamilyCategory
        if rvt_cat is not None:
            return PkCategory(rvt_cat)

    @property
    def family_category_id(self):
        rvt_cat_id = self._rvt_obj.FamilyCategoryId
        if rvt_cat_id is not None:
            return PkElementId(rvt_cat_id)

    def get_family_symbol_ids(self):
        return [PkElementId(sid) for sid in self._rvt_obj.GetFamilySymbolIds()]

    def get_family_symbols(self):
        # type: () -> list[PkFamilySymbol]
        return [
            eid.get_element(self.doc) for eid in self.get_family_symbol_ids()
        ]


class PkInstance(PkElement):
    _RVT_TYPE = DB.Instance

    def __init__(self, rvt_instance):
        # type: (DB.Instance) -> None
        self._validate_type(rvt_instance, self._RVT_TYPE)
        self._rvt_obj = rvt_instance  # type: DB.Instance

    @property
    def unwrap(self):
        return self._rvt_obj


class PkRevisionCloud(PkElement):
    _RVT_TYPE = DB.RevisionCloud

    def __init__(self, rvt_obj):
        # type: (DB.RevisionCloud) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.RevisionCloud

    @property
    def unwrap(self):
        return self._rvt_obj


class PkDatumPlane(PkElement):
    _RVT_TYPE = DB.DatumPlane

    def __init__(self, rvt_obj):
        # type: (DB.DatumPlane) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.DatumPlane

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_curves_in_view(self, datum_type, view):
        # type: (DB.DatumExtentType, PkView) -> list[PkCurve]
        rvt_curves = self._rvt_obj.GetCurvesInView(datum_type, view.unwrap)
        return [PkCurve.wrap(c) for c in rvt_curves]


class PkLevel(PkDatumPlane):
    _RVT_TYPE = DB.Level

    def __init__(self, rvt_obj):
        # type: (DB.Level) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Level

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def elevation(self):
        # type: () -> float
        return self._rvt_obj.Elevation


class PkFamilyInstance(PkInstance):
    _RVT_TYPE = DB.FamilyInstance

    def __init__(self, rvt_obj):
        # type: (DB.FamilyInstance) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.FamilyInstance

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_transform(self):
        rvt_transform = self._rvt_obj.GetTransform()
        if rvt_transform is not None:
            return PkTransform(rvt_transform)

    @property
    def mirrored(self):
        # type: () -> bool
        return self._rvt_obj.Mirrored

    @property
    def location(self):
        # type: () -> PkLocation
        return PkLocation.wrap(self._rvt_obj.Location)

    @property
    def facing_orientation(self):
        return PkXYZ(self._rvt_obj.FacingOrientation)

    @property
    def hand_orientation(self):
        return PkXYZ(self._rvt_obj.HandOrientation)

    @property
    def mep_model(self):
        # type: () -> PkMEPModel | None
        rvt_mep_model = self._rvt_obj.MEPModel
        if rvt_mep_model is not None:
            return PkMEPModel.wrap(rvt_mep_model)

    @property
    def host(self):
        # type: () -> PkElement | None
        rvt_host = self._rvt_obj.Host
        if rvt_host is not None:
            return PkElement.wrap(rvt_host)

    @property
    def symbol(self):
        return PkFamilySymbol(self._rvt_obj.Symbol)

    @symbol.setter
    def symbol(self, value):
        # type: (PkFamilySymbol) -> None
        self._rvt_obj.Symbol = value.unwrap


class PkRevitLinkInstance(PkInstance):
    _RVT_TYPE = DB.RevitLinkInstance

    def __init__(self, rvt_link_instance):
        # type: (DB.RevitLinkInstance) -> None
        self._validate_type(rvt_link_instance, self._RVT_TYPE)
        self._rvt_obj = rvt_link_instance  # type: DB.RevitLinkInstance

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_link_document(self):
        return PkDocument(self._rvt_obj.GetLinkDocument())


class PkTextElement(PkElement):
    _RVT_TYPE = DB.TextElement

    def __init__(self, txt_elem):
        # type: (DB.TextElement) -> None
        self._validate_type(txt_elem, self._RVT_TYPE)
        self._rvt_obj = txt_elem  # type: DB.TextElement

    @property
    def unwrap(self):
        return self._rvt_obj


class PkTextNote(PkTextElement):
    _RVT_TYPE = DB.TextNote

    def __init__(self, txt_elem):
        # type: (DB.TextNote) -> None
        self._validate_type(txt_elem, self._RVT_TYPE)
        self._rvt_obj = txt_elem  # type: DB.TextNote

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def text(self):
        # type: () -> str
        return self._rvt_obj.Text

    @text.setter
    def text(self, txt):
        # type: (str) -> None
        self._rvt_obj.Text = txt


class PkElementType(PkElement):
    _RVT_TYPE = DB.ElementType

    def __init__(self, rvt_obj):
        # type: (DB.ElementType) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ElementType

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def name(self):
        name_param = self.get_parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM)
        return name_param.as_string

    @property
    def family_name(self):
        # type: () -> str
        return self._rvt_obj.FamilyName


class PkLineAndTextAttrSymbol(PkElementType):
    _RVT_TYPE = DB.LineAndTextAttrSymbol

    def __init__(self, rvt_obj):
        # type: (DB.LineAndTextAttrSymbol) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.LineAndTextAttrSymbol

    @property
    def unwrap(self):
        return self._rvt_obj


class PkTextElementType(PkLineAndTextAttrSymbol):
    _RVT_TYPE = DB.TextElementType

    def __init__(self, rvt_obj):
        # type: (DB.TextElementType) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.TextElementType

    @property
    def unwrap(self):
        return self._rvt_obj


class PkTextNoteType(PkTextElementType):
    _RVT_TYPE = DB.TextNoteType

    def __init__(self, rvt_obj):
        # type: (DB.TextNoteType) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.TextNoteType

    @property
    def unwrap(self):
        return self._rvt_obj


class PkInsertableObject(PkElementType):
    _RVT_TYPE = DB.InsertableObject

    def __init__(self, rvt_obj):
        # type: (DB.InsertableObject) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.InsertableObject

    @property
    def unwrap(self):
        return self._rvt_obj


class PkViewFamilyType(PkElementType):
    _RVT_TYPE = DB.ViewFamilyType

    def __init__(self, view_type):
        # type: (DB.ViewFamilyType) -> None
        self._validate_type(view_type, self._RVT_TYPE)
        self._rvt_obj = view_type  # type: DB.ViewFamilyType

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def default_template(self):
        # type: () -> PkView
        rvt_id = self._rvt_obj.DefaultTemplateId
        return PkElementId(rvt_id).get_element(self.doc)


class PkGroup(PkElement):
    _RVT_TYPE = DB.Group

    def __init__(self, elem_type):
        # type: (DB.Group) -> None
        self._validate_type(elem_type, self._RVT_TYPE)
        self._rvt_obj = elem_type  # type: DB.Group

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_member_ids(self):
        return [PkElementId(id) for id in self._rvt_obj.GetMemberIds()]

    @property
    def members(self):
        return [id.get_element(self.doc) for id in self.get_member_ids()]

    @property
    def location(self):
        # type: () -> PkLocationPoint
        return PkLocationPoint(self._rvt_obj.Location)

    @property
    def deepest_members(self):
        # type: () -> list[PkElement]
        return list(self._yield_deeper_members())

    def walk_members(self):
        """list of lists (...of lists, etc.) of deepest members"""
        return self._get_deeper_members()

    def _yield_deeper_members(self):
        for member in self.members:
            if isinstance(member, PkGroup):
                for sub_member in member._yield_deeper_members():
                    yield sub_member
            else:
                yield member

    def _get_deeper_members(self):
        sub_members = []
        for member in self.members:
            if isinstance(member, PkGroup):
                sub_members.append(member._get_deeper_members())
            else:
                sub_members.append(member)
        return sub_members


class PkView(PkElement):
    _RVT_TYPE = DB.View

    def __init__(self, view):
        # type: (DB.View) -> None
        self._validate_type(view, self._RVT_TYPE)
        self._rvt_obj = view  # type: DB.View

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def name(self):
        # type: () -> str | None
        return self._rvt_obj.Name

    @name.setter
    def name(self, new_name):
        # type: (str) -> None
        self._rvt_obj.Name = new_name

    @property
    def rvt_crop_box(self):
        # type: () -> DB.BoundingBoxXYZ
        return self._rvt_obj.CropBox

    @rvt_crop_box.setter
    def rvt_crop_box(self, revt_bb):
        # type: (DB.BoundingBoxXYZ) -> None
        self._rvt_obj.CropBox = revt_bb

    @property
    def crop_box_active(self):
        # type: () -> bool
        return self._rvt_obj.CropBoxActive

    @crop_box_active.setter
    def crop_box_active(self, is_active):
        # type: (bool) -> None
        self._rvt_obj.CropBoxActive = is_active

    @property
    def crop_box_visible(self):
        # type: () -> bool
        return self._rvt_obj.CropBoxVisible

    @crop_box_visible.setter
    def crop_box_visible(self, is_visible):
        # type: (bool) -> None
        self._rvt_obj.CropBoxVisible = is_visible

    @property
    def rvt_origin(self):
        return self._rvt_obj.Origin

    @property
    def origin(self):
        return PkXYZ(self.rvt_origin)

    @property
    def view_direction(self):
        return PkXYZ(self.rvt_view_direction)

    @property
    def up_direction(self):
        return PkXYZ(self._rvt_obj.UpDirection)

    @property
    def right_direction(self):
        return PkXYZ(self._rvt_obj.RightDirection)

    @property
    def sketch_plane(self):
        return PkSketchPlane(self._rvt_obj.SketchPlane)

    @sketch_plane.setter
    def sketch_plane(self, value):
        # type: (PkSketchPlane) -> None
        self._rvt_obj.SketchPlane = value.unwrap

    @property
    def crop_box(self):
        crop_box = self.rvt_crop_box
        if crop_box is None:
            raise pke.BoundingBoxNotFoundError(
                'Failed getting crop box from view {} '
                .format(self.id)
            )
        return PkBoundingBoxXYZ(crop_box)

    @property
    def gen_level(self):
        rvt_lvl = self._rvt_obj.GenLevel
        if rvt_lvl is not None:
            return PkLevel(rvt_lvl)

    @property
    def rvt_view_direction(self):
        # type: () -> DB.XYZ
        return self._rvt_obj.ViewDirection

    @property
    def view_template_id(self):
        return PkElementId(self._rvt_obj.ViewTemplateId)

    @property
    def title(self):
        # type: () -> str
        return self._rvt_obj.Title

    @property
    def view_template(self):
        # type: () -> PkView
        return self.view_template_id.get_element(self.doc)

    @view_template.setter
    def view_template(self, template):
        # type: (PkView) -> None
        self._rvt_obj.ViewTemplateId = template.id.unwrap

    @crop_box.setter
    def crop_box(self, pk_bb):
        # type: (PkBoundingBoxXYZ) -> None
        self.rvt_crop_box = pk_bb.unwrap

    @property
    def plane(self):
        return PkPlane.new_by_rvt_origin_and_basis(
            self._rvt_obj.Origin,
            self._rvt_obj.RightDirection,
            self._rvt_obj.UpDirection
        )

    def get_crop_manager(self):
        rvt_crop_manager = self._rvt_obj.GetCropRegionShapeManager()
        return PkViewCropRegionShapeManager(rvt_crop_manager)

    def duplicate(self, duplication_opts):
        # type: (DB.ViewDuplicateOption) -> Self
        rvt_view_id = self._rvt_obj.Duplicate(duplication_opts)
        return self.doc.get_element(PkElementId(rvt_view_id))

    @property
    def is_plan(self):
        # type: () -> bool
        return self._rvt_obj.ViewType in [
            DB.ViewType.FloorPlan,
            DB.ViewType.CeilingPlan,
            DB.ViewType.AreaPlan,
            DB.ViewType.EngineeringPlan
        ]

    @property
    def is_floor_plan(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.FloorPlan

    @property
    def is_ceiling_plan(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.CeilingPlan

    @property
    def is_3d(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.ThreeD

    @property
    def is_detail(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.Detail

    @property
    def is_drafting(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.DraftingView

    @property
    def is_legend(self):
        # type: () -> bool
        return self._rvt_obj.ViewType == DB.ViewType.DraftingView

    @property
    def annotation_crop(self):
        return bool(self._get_anno_crop_param().as_integer)

    @annotation_crop.setter
    def annotation_crop(self, value):
        # type: (bool) -> None
        self._get_anno_crop_param().value = int(value)

    def _get_anno_crop_param(self):
        ANNO_CROP_BIP = DB.BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE
        anno_crop_param = self.get_parameter(ANNO_CROP_BIP)

        if anno_crop_param is not None:
            return anno_crop_param

        raise pke.ParameterNotFoundError(
            'view "{}" does not have parameter "{}"'
            .format(self, ANNO_CROP_BIP)
        )

    @property
    def _scope_box_param(self):
        SCOPE_BOX_BIP = DB.BuiltInParameter.VIEWER_VOLUME_OF_INTEREST_CROP
        scope_box_param = self.get_parameter(SCOPE_BOX_BIP)

        if scope_box_param is None:
            raise pke.ParameterNotFoundError(
                'View id<{}> does not have parameter "{}"'
                .format(self.id.value, SCOPE_BOX_BIP)
            )

        return scope_box_param

    @property
    def scope_box_id(self):
        return self._scope_box_param.as_element_id

    @scope_box_id.setter
    def scope_box_id(self, value):
        # type: (PkElementId) -> None
        self._scope_box_param.value = value


class ViewsForSheet(PkView):
    _RVT_TYPE = tuple([
        DB.ViewSection,
        DB.TableView,
        DB.View3D,
        DB.ViewDrafting,
        DB.ViewPlan,
    ])

    def place_on_sheet(self, sheet, location):
        # type: (PkViewSheet, PkXYZ) -> PkViewport
        return PkViewport.create(self.doc, sheet, self, location)

    @property
    def title_on_sheet(self):
        param = self.get_parameter(DB.BuiltInParameter.VIEW_DESCRIPTION)
        return param.as_string

    @title_on_sheet.setter
    def title_on_sheet(self, title):
        # type: (str) -> None
        param = self.get_parameter(DB.BuiltInParameter.VIEW_DESCRIPTION)
        param.value = title


class PkTableView(ViewsForSheet):
    _RVT_TYPE = DB.TableView

    def __init__(self, rvt_obj):
        # type: (DB.TableView) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.TableView

    @property
    def unwrap(self):
        return self._rvt_obj


class PkViewPlan(ViewsForSheet):
    _RVT_TYPE = DB.ViewPlan

    def __init__(self, rvt_obj):
        # type: (DB.ViewPlan) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ViewPlan

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_view_range(self):
        return PkPlanViewRange(self._rvt_obj.GetViewRange())

    def set_view_range(self, view_range):
        # type: (PkPlanViewRange) -> None
        self._rvt_obj.SetViewRange(view_range.unwrap)

    def check_plan_view_range(self, view_range):
        # type: (PkPlanViewRange) -> list[DB.PlanViewRangeError]
        errors = self._rvt_obj.CheckPlanViewRangeValidity(view_range.unwrap)
        return [err for err in errors]


class PkViewSchedule(ViewsForSheet):
    _RVT_TYPE = DB.ViewSchedule

    def __init__(self, rvt_obj):
        # type: (DB.ViewSchedule) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ViewSchedule

    @property
    def unwrap(self):
        return self._rvt_obj


class PkViewSection(ViewsForSheet):
    _RVT_TYPE = DB.ViewSection

    def __init__(self, view):
        # type: (DB.ViewSection) -> None
        self._validate_type(view, self._RVT_TYPE)
        self._rvt_obj = view  # type: DB.ViewSection

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def create_section(cls, doc, view_fam_type, view_box):
        # type: (PkDocument, PkViewFamilyType, PkViewSectionBox) -> PkViewSection  # noqa
        rvt_sectoin = cls._rvt_obj.CreateSection(
            doc.unwrap,
            view_fam_type.unwrap.Id,
            view_box.bb.unwrap
        )
        return cls(rvt_sectoin)

    @property
    def section_box(self):
        return PkViewSectionBox(self.crop_box)

    @section_box.setter
    def section_box(self, new_section_box):
        # type: (PkViewSectionBox) -> None
        self.crop_box = new_section_box.bb


class PkViewSectionBox(BasePKObject):
    """https://gist.github.com/nodatasheet/665d0a148705d62fef28855cf06550d2"""

    def __init__(self, pk_bb):
        # type: (PkBoundingBoxXYZ) -> None
        self._bb = pk_bb

    @property
    def bb(self):
        return self._bb


class PkViewport(PkElement):
    _RVT_TYPE = DB.Viewport

    def __init__(self, rvt_obj):
        # type: (DB.Viewport) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Viewport

    @property
    def unwrap(self):
        return self._rvt_obj  # type: DB.Viewport

    @classmethod
    def create(cls, doc, sheet, view, location):
        # type: (PkDocument, PkViewSheet, PkView, PkXYZ) -> Self
        rvt_view = DB.Viewport.Create(
            doc.unwrap,
            sheet.id.unwrap,
            view.id.unwrap,
            location.unwrap
        )
        return cls(rvt_view)

    @property
    def view_id(self):
        return PkElementId(self._rvt_obj.ViewId)

    @property
    def view(self):
        # type: () -> PkView
        return self.view_id.get_element(self.doc)

    @property
    def title_on_sheet(self):
        param = self.get_parameter(DB.BuiltInParameter.VIEW_DESCRIPTION)
        return param.as_string

    @title_on_sheet.setter
    def title_on_sheet(self, title):
        # type: (str) -> None
        param = self.get_parameter(DB.BuiltInParameter.VIEW_DESCRIPTION)
        param.value = title

    @property
    def sheet_id(self):
        return PkElementId(self._rvt_obj.SheetId)

    @property
    def sheet(self):
        # type: () -> PkViewSheet
        return self.sheet_id.get_element(self.doc)


class PkViewSheet(PkView):
    _RVT_TYPE = DB.ViewSheet

    def __init__(self, rvt_obj):
        # type: (DB.ViewSheet) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ViewSheet

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_all_viewports(self):
        # type: () -> list[PkViewport]
        viewports = []
        for vp_id in self._rvt_obj.GetAllViewports():
            vp = PkElementId(vp_id).get_element(self.doc)
            viewports.append(vp)
        return viewports

    @property
    def sheet_number(self):
        # type: () -> str
        return self._rvt_obj.SheetNumber


class PkView3D(ViewsForSheet):
    _RVT_TYPE = DB.View3D

    def __init__(self, view):
        # type: (DB.View) -> None
        self._validate_type(view, self._RVT_TYPE)
        self._rvt_obj = view  # type: DB.View3D

    @property
    def unwrap(self):
        return self._rvt_obj


class PkTag(PkElement):
    _RVT_TYPE = DB.IndependentTag

    def __init__(self, tag):
        # type: (DB.IndependentTag) -> None
        self._validate_type(tag, self._RVT_TYPE)
        self._rvt_obj = tag  # type: DB.IndependentTag

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_tagged_elem_ids(self):
        # type: () -> list[PkLinkOrHostElementId]
        ids = []
        for id in self._rvt_obj.GetTaggedElementIds():
            ids.append(PkLinkOrHostElementId(id))
        return ids

    def get_tagged_local_elems(self):
        # type: () -> list[PkElement]
        return [
            PkElement.wrap(e) for e in self._rvt_obj.GetTaggedLocalElements()
        ]

    @property
    def rvt_head_position(self):
        return self._rvt_obj.TagHeadPosition

    @rvt_head_position.setter
    def rvt_head_position(self, value):
        # type: (DB.XYZ) -> None
        self._rvt_obj.TagHeadPosition = value

    @property
    def has_leader(self):
        return self._rvt_obj.HasLeader

    @has_leader.setter
    def has_leader(self, status):
        # type: (bool) -> None
        self._rvt_obj.HasLeader = status

    @property
    def rvt_leader_end_condition(self):
        return self._rvt_obj.LeaderEndCondition

    @rvt_leader_end_condition.setter
    def rvt_leader_end_condition(self, condition):
        # type: (DB.LeaderEndCondition) -> None
        self._rvt_obj.LeaderEndCondition = condition

    @property
    def tag_orientation(self):
        orientation = PkTagOrientation(
            self._rvt_obj.TagOrientation
        )  # type: PkTagOrientation
        orientation.parent_tag = self
        return orientation

    @property
    def tag_text(self):
        # type: () -> str
        return self._rvt_obj.TagText


class PkTagOrientation(BasePKWrapper):
    _RVT_TYPE = DB.TagOrientation

    def __init__(self, orientation):
        # type: (DB.TagOrientation) -> None
        self._validate_type(orientation, self._RVT_TYPE)
        self._rvt_obj = orientation  # type: DB.TagOrientation
        self._parent_tag = None  # type: PkTag

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def parent_tag(self):
        return self._parent_tag

    @parent_tag.setter
    def parent_tag(self, tag):
        # type: (PkTag) -> None
        self._parent_tag = tag

    def make_vertical(self):
        self._validate_has_parent()
        self._parent_tag.unwrap.TagOrientation = DB.TagOrientation.Vertical

    def make_horizontal(self):
        self._validate_has_parent()
        self._parent_tag.unwrap.TagOrientation = DB.TagOrientation.Horizontal

    def make_model(self):
        self._validate_has_parent()
        self._parent_tag.unwrap.TagOrientation = \
            DB.TagOrientation.AnyModelDirection

    def _validate_has_parent(self):
        if self._parent_tag is None:
            raise pke.ValidationError(
                '<{}> object does not have parent tag.'
                .format(type(self).__name__)
            )

    @property
    def is_vertical(self):
        # type: () -> bool
        return self._rvt_obj == DB.TagOrientation.Vertical

    @property
    def is_horizontal(self):
        # type: () -> bool
        return self._rvt_obj == DB.TagOrientation.Horizontal

    @property
    def is_model(self):
        # type: () -> bool
        return self._rvt_obj == DB.TagOrientation.AnyModelDirection


class PkFamilySymbol(PkInsertableObject):
    _RVT_TYPE = DB.FamilySymbol

    def __init__(self, family_symbol):
        # type: (DB.FamilySymbol) -> None
        self._validate_type(family_symbol, self._RVT_TYPE)
        self._rvt_obj = family_symbol  # type: DB.FamilySymbol

    @property
    def unwrap(self):
        return self._rvt_obj

    def activate(self):
        """
        Activates the symbol to ensure that its geometry is accessible.
        """
        self._rvt_obj.Activate()

    @property
    def is_active(self):
        # type: () -> bool
        return self._rvt_obj.IsActive

    @property
    def family(self):
        rvt_family = self._rvt_obj.Family
        if rvt_family is not None:
            return PkFamily.wrap(rvt_family)


class PkParameter(BasePKWrapper):
    _RVT_TYPE = DB.Parameter

    def __init__(self, param):
        # type: (DB.Parameter) -> None
        self._validate_type(param, self._RVT_TYPE)
        self._rvt_obj = param  # type: DB.Parameter
        self._name = param.Definition.Name
        self._storage_type = param.StorageType

    def __str__(self):
        return (
            '{}[rvt_type <{}> (name: {}, id: {})]'
            .format(
                self.__class__.__name__,
                type(self._rvt_obj).__name__,
                self.name,
                self.id.value
            )
        )

    def __eq__(self, other):
        # type: (PkParameter) -> bool
        return self.doc == other.doc and self.id == other.id

    def __ne__(self, other):
        # type: (PkParameter) -> bool
        return not self.__eq__(other)

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def doc(self):
        return PkDocument(self._rvt_obj.Element.Document)

    @property
    def element(self):
        return PkElement.wrap(self._rvt_obj.Element)

    @property
    def name(self):
        return self._name

    @property
    def guid_or_id(self):
        # type: () -> Guid | PkElementId
        return self.guid or self.id

    @property
    def id(self):
        return PkElementId(self._rvt_obj.Id)

    @property
    def guid(self):
        # type: () -> Guid | None
        if self.is_shared:
            return self._rvt_obj.GUID

    @property
    def has_value(self):
        return self._rvt_obj.HasValue

    @property
    def value(self):
        # type: () -> int | float | str | PkElementId | None
        if self.is_integer:
            return self.as_integer

        if self.is_double:
            return self.as_double

        if self.is_string:
            return self.as_string

        if self.is_element_id:
            return self.as_element_id

    @property
    def as_element_id(self):
        return PkElementId(self._rvt_obj.AsElementId())

    @property
    def as_string(self):
        # type: () -> str
        return self._rvt_obj.AsString()

    @property
    def as_double(self):
        # type: () -> float
        return self._rvt_obj.AsDouble()

    @property
    def as_integer(self):
        # type: () -> int
        return self._rvt_obj.AsInteger()

    @property
    def is_element_id(self):
        # type: () -> bool
        return self._storage_type == DB.StorageType.ElementId

    @property
    def is_string(self):
        # type: () -> bool
        return self._storage_type == DB.StorageType.String

    @property
    def is_double(self):
        # type: () -> bool
        return self._storage_type == DB.StorageType.Double

    @property
    def is_integer(self):
        # type: () -> bool
        return self._storage_type == DB.StorageType.Integer

    @property
    def is_shared(self):
        # type: () -> bool
        return self._rvt_obj.IsShared

    @value.setter
    def value(self, new_value):
        # type: (int | float | str | PkElementId) -> bool
        self._validate_type(new_value, tuple([int, float, str, PkElementId]))

        if self._rvt_obj.IsReadOnly:
            raise pke.ParameterIsReadOnlyError(
                'parameter "{}" is read only'.format(self._name)
            )

        if isinstance(new_value, PkElementId):
            return self._rvt_obj.Set(new_value.unwrap)

        return self._rvt_obj.Set(new_value)


class PkOutline(BasePKWrapper):
    _RVT_TYPE = DB.Outline

    def __init__(self, rvt_obj):
        # type: (DB.Outline) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Outline

    def __str__(self):
        return (
            self.__class__.__name__
            + '('
            + 'Min'
            + str(self.min.coordinates)
            + ', '
            + 'Max'
            + str(self.max.coordinates)
            + ')'
        )

    @property
    def min(self):
        return PkXYZ(self._rvt_obj.MinimumPoint)

    @property
    def max(self):
        return PkXYZ(self._rvt_obj.MaximumPoint)


class PkBoundingBoxXYZ(BasePKWrapper):
    _RVT_TYPE = DB.BoundingBoxXYZ

    def __init__(self, rvt_obj):
        # type: (DB.BoundingBoxXYZ) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.BoundingBoxXYZ

    def __str__(self):
        return (
            self.__class__.__name__
            + '('
            + 'Min'
            + str(self.min.coordinates)
            + ', '
            + 'Max'
            + str(self.max.coordinates)
            + ')'
        )

    @classmethod
    def new_by_minmax(cls, min, max):
        # type: (PkXYZ, PkXYZ) -> PkBoundingBoxXYZ
        bb = DB.BoundingBoxXYZ()
        bb.Min = min.unwrap
        bb.Max = max.unwrap
        return cls(bb)

    @classmethod
    def new_by_points(cls, points):
        # type: (Iterable[PkXYZ]) -> PkBoundingBoxXYZ
        new_bb = cls.new_by_minmax(*points[:2])
        for point in points:
            new_bb.add_point(point)

        return new_bb

    def contains_point(self, point, tolerance=0.0):
        # type: (PkXYZ, float) -> bool
        rvt_outline = self.get_rvt_outline()
        return rvt_outline.Contains(point.unwrap, tolerance)

    def add_point(self, point):
        # type: (PkXYZ) -> None
        rvt_outline = self.get_rvt_outline()
        rvt_outline.AddPoint(point.unwrap)
        self._rvt_obj = self._outline_to_bbox(rvt_outline)

    def add_box(self, pk_box):
        # type: (PkBoundingBoxXYZ) -> None
        self.add_point(pk_box.min)
        self.add_point(pk_box.max)

    def to_cuboid(self):
        return PkCuboid.new_by_doagonal_corners(self.diagonal_corners)

    def to_outline(self):
        return PkOutline(self.get_rvt_outline())

    def drop_z(self):
        """
        Creates a new PkBoundingBoxXYZ with same x and y coordinates,
        but z = 0.
        """
        return self.new_by_minmax(self.min.drop_z(), self.max.drop_z())

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def diagonal_corners(self):
        return self.min, self.max

    @property
    def all_corners(self):
        # type: () -> list[PkXYZ]
        bb_min = self.min
        bb_max = self.max
        xs = bb_min.x, bb_max.x
        ys = bb_min.y, bb_max.y
        zs = bb_min.z, bb_max.z
        corners = []
        for x, y, z in itertools.product(xs, ys, zs):
            p = PkXYZ.new(x, y, z)
            corners.append(p)
        return corners

    @property
    def min(self):
        return PkXYZ(self._rvt_obj.Min)

    @min.setter
    def min(self, pk_xyz):
        # type: (PkXYZ) -> None
        self._rvt_obj.Min = pk_xyz.unwrap

    @property
    def max(self):
        return PkXYZ(self._rvt_obj.Max)

    @max.setter
    def max(self, pk_xyz):
        # type: (PkXYZ) -> None
        self._rvt_obj.Max = pk_xyz.unwrap

    @property
    def rvt_min(self):
        return self._rvt_obj.Min

    @rvt_min.setter
    def rvt_min(self, value):
        # type: (float) -> None
        self._rvt_obj.Min = value

    @property
    def rvt_max(self):
        return self._rvt_obj.Max

    @rvt_max.setter
    def rvt_max(self, value):
        # type: (float) -> None
        self._rvt_obj.Max = value

    @property
    def rvt_center(self):
        # type: () -> DB.XYZ
        return (self.rvt_max + self.rvt_min) / 2

    @property
    def dx(self):
        # type: () -> float
        """Max.X - Min.X"""
        return self._rvt_obj.Max.X - self._rvt_obj.Min.X

    @property
    def dy(self):
        # type: () -> float
        """Max.Y - Min.Y"""
        return self._rvt_obj.Max.Y - self._rvt_obj.Min.Y

    @property
    def dz(self):
        # type: () -> float
        """Max.Z - Min.Z"""
        return self._rvt_obj.Max.Z - self._rvt_obj.Min.Z

    @property
    def center(self):
        return PkXYZ(self.rvt_center)

    @property
    def transform(self):
        return PkTransform(self._rvt_obj.Transform)

    @transform.setter
    def transform(self, value):
        # type: (PkTransform) -> None
        self._rvt_obj.Transform = value.unwrap

    def get_rvt_outline(self):
        # type: () -> DB.Outline
        return self._bbox_to_outline(self.unwrap)

    def _bbox_to_outline(self, bounding_box):
        # type: (DB.BoundingBoxXYZ) -> DB.Outline
        return DB.Outline(bounding_box.Min, bounding_box.Max)

    def _outline_to_bbox(self, outline):
        # type: (DB.Outline) -> DB.BoundingBoxXYZ
        bbox = DB.BoundingBoxXYZ()
        bbox.Min = outline.MinimumPoint
        bbox.Max = outline.MaximumPoint
        return bbox


class BasePkCoordinates(BasePKWrapper):

    _coordinates = tuple()   # type: tuple[float]
    _rvt_obj = None  # type: DB.XYZ | DB.UV

    def __new__(cls, *args, **kwargs):
        if cls is BasePkCoordinates:
            raise NotImplementedError(
                'Creating instances of {} class is not allowed.'
                .format(cls.__name__)
            )
        return super(BasePkCoordinates, cls).__new__(cls)

    def __str__(self):
        return self.__class__.__name__ + str(self._coordinates)

    def __abs__(self):
        """Returns the distance between these coordinates and the origin."""
        return self.distance_to(self._zero)

    def __contains__(self, item):
        # type: (Self) -> bool
        return item in self._coordinates

    def __getitem__(self, key):
        # type: (int) -> Self
        return self._coordinates[key]

    def __iter__(self):
        return self._coordinates.__iter__()

    def __len__(self):
        return len(self._coordinates)

    def __mul__(self, factor):
        return self.multiply(factor)

    def __rmul__(self, factor):
        return self.__mul__(factor)

    def __neg__(self):
        return self.negate()

    def __add__(self, other):
        # type: (BasePkCoordinates) -> BasePkCoordinates
        return self.add(other)

    def __sub__(self, other):
        # type: (Self) -> Self
        return self.substract(other)

    def __lt__(self, other):
        # type: (BasePkCoordinates) -> bool
        raise NotImplementedError()

    def __eq__(self, other):
        # type: (BasePkCoordinates) -> bool
        """Check coordinates equality using `almost_equal()` method
        with the default Revit tolerance.

        For more precise equality, use `almost_equal()`
        with specified tolerance.
        """
        return self.almost_equal(other)

    def __ne__(self, other):
        # type: (BasePkCoordinates) -> bool
        return not self.__eq__(other)

    def __gt__(self, other):
        # type: (BasePkCoordinates) -> bool
        return not self.__lt__(other) and self.__ne__(other)

    def __le__(self, other):
        # type: (BasePkCoordinates) -> bool
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        # type: (BasePkCoordinates) -> bool
        return not self.__lt__(other)

    def almost_equal(self, other, tolerance=None):
        # type: (Self, float) -> bool
        """Checks whether these coordinates and other coordinates are the same
        withing a specified tolerance.

        If no tolerance specified, used Revit default tolerance
        of coordinates comparison.
        """
        if tolerance is not None:
            return self._rvt_obj.IsAlmostEqualTo(other._rvt_obj, tolerance)
        return self._rvt_obj.IsAlmostEqualTo(other._rvt_obj)

    def bisector(self, other):
        # type: (Self) -> Self
        self._validate_type(other, type(self))
        return self.normalize() + other.normalize()

    def clone(self):
        # type: () -> Self
        return self._wrap_to_self(self._rvt_obj)

    def angle_to(self, other):
        # type: (Self) -> float
        return self._rvt_obj.AngleTo(other.unwrap)

    def distance_to(self, other):
        # type: (Self) -> float
        """Returns the distance from these coordinates
        to the specified coordinates.
        """
        return self._rvt_obj.DistanceTo(other._rvt_obj)

    def dot_product(self, other):
        # type: (Self) -> float
        """The dot product of vector with these coordinates
        and the vector of other coordinates."""
        return self._rvt_obj.DotProduct(other._rvt_obj)

    def cross_product(self, other):
        # type: (Self) -> Self
        """The cross product of vector with these coordinates
        and the vector of other coordinates."""
        return self._wrap_to_self(
            self._rvt_obj.CrossProduct(other._rvt_obj)
        )

    def add(self, other):
        # type: (Self) -> Self
        """Adds other coordinates to self."""
        return self._wrap_to_self(
            self._rvt_obj.Add(other._rvt_obj)
        )

    def taxicab_distance(self, other):
        # type: (Self) -> float
        """
        The Taxicab Distance from self to other.

        Returns the sum of the horizontal and vertical distances
        from self to other.
        """
        return sum(abs(a - b) for a, b in zip(self, other))

    def substract(self, other):
        # type: (Self) -> Self
        """Subtracts other coordinates from self."""
        return self._wrap_to_self(
            self._rvt_obj.Subtract(other._rvt_obj)
        )

    def multiply(self, other):
        # type: (float) -> Self
        """Multiples coordinates by a factor."""
        return self._wrap_to_self(
            self._rvt_obj.Multiply(other)
        )

    def negate(self):
        # type: () -> Self
        """Negates the coordinates."""
        return self._wrap_to_self(
            self._rvt_obj.Negate()
        )

    def normalize(self):
        # type: () -> Self
        return self._wrap_to_self(self._rvt_obj.Normalize())

    def is_parallel(self, other, tolerance=1e-9):
        # type: (Self, float) -> bool
        """Tolerance is for comparison with dot product."""
        abs_dot_prod = abs(self.dot_product(other))
        return math_utils.almost_eq(abs_dot_prod, 1.0, rel_tol=tolerance)

    def is_codirectional(self, other, tolerance=1e-9):
        # type: (Self, float) -> bool
        """Tolerance is for comparison with dot product."""
        return math_utils.almost_eq(
            self.dot_product(other),
            1.0,
            rel_tol=tolerance
        )

    def is_orthogonal(self, other, tolerance=1e-9):
        # type: (Self, float) -> bool
        """Tolerance is for comparison with dot product."""
        return math_utils.almost_eq(
            self.dot_product(other),
            0,
            rel_tol=tolerance,
            abs_tol=1e-9
        )

    def get_length(self):
        # type: () -> float
        return self._rvt_obj.GetLength()

    @property
    def coordinates(self):
        # type: () -> tuple[float]
        return self._coordinates

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def _zero(self):
        """Zero coordinates."""
        return self._wrap_to_self(self._rvt_obj.Zero)

    @property
    def is_zero_length(self):
        # type: () -> bool
        """True if every coordinate is zero within Revit tolerance."""
        return self._rvt_obj.IsZeroLength()


class PkUV(BasePkCoordinates):
    _RVT_TYPE = DB.UV

    def __init__(self, uv):
        # type: (DB.UV) -> None
        self._validate_type(uv, self._RVT_TYPE)
        self._rvt_obj = uv  # type: DB.UV
        self._coordinates = (self._rvt_obj.U,
                             self._rvt_obj.V)

    def __lt__(self, other):
        # type: (PkUV) -> bool
        """Are these coordinates smaller than other.

        Using lexicographic ordering:
        https://math.stackexchange.com/a/54657

        p1.x < p2.x

        or p1.x = p2.x and p1.y < p2.y

        Equality is approximate.
        """
        self._validate_type(other, PkUV)

        if self.u < other.u:
            return True

        if math_utils.almost_eq(self.u, other.u) and self.v < other.v:
            return True

        return False

    @classmethod
    def new(cls, u, v):
        # type: (float, float) -> PkUV
        return cls(DB.UV(u, v))

    @classmethod
    def zero(cls):
        return cls(DB.UV.Zero)

    @classmethod
    def basis_u(cls):
        return cls(DB.UV.BasisU)

    @classmethod
    def basis_v(cls):
        return cls(DB.UV.BasisV)

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def u(self):
        # type: () -> float
        return self._rvt_obj.U

    @property
    def v(self):
        # type: () -> float
        return self._rvt_obj.V

    def as_pk_xyz_on_plane(self, pk_plane):
        # type: (PkPlane) -> PkXYZ
        return (
            pk_plane.origin
            + self.u * pk_plane.x_dir
            + self.v * pk_plane.y_dir
        )


class PkXYZ(BasePkCoordinates):
    _RVT_TYPE = DB.XYZ

    def __init__(self, xyz):
        # type: (DB.XYZ) -> None
        self._validate_type(xyz, self._RVT_TYPE)
        self._rvt_obj = xyz  # type: DB.XYZ
        self._coordinates = (self._rvt_obj.X,
                             self._rvt_obj.Y,
                             self._rvt_obj.Z)

    def __lt__(self, other):
        # type: (PkXYZ) -> bool
        """Are these coordinates smaller than other.

        Using lexicographic ordering:
        https://math.stackexchange.com/a/54657

        p1.x < p2.x

        or p1.x = p2.x and p1.y = p2.y

        or p1.x = p2.x and p1.y = p2.y and p1.z < p2.z

        Equality is approximate.
        """
        self._validate_type(other, PkXYZ)

        if self.x < other.x:
            return True

        if math_utils.almost_eq(self.x, other.x):
            if self.y < other.y:
                return True

            if self.z < other.z and math_utils.almost_eq(self.y, other.y):
                return True

        return False

    @classmethod
    def new(cls, x, y, z):
        # type: (float, float, float) -> PkXYZ
        return cls(DB.XYZ(x, y, z))

    @classmethod
    def zero(cls):
        """Creates a new PkXYZ with 0, 0, 0 coordinates."""
        return cls(DB.XYZ.Zero)

    @classmethod
    def basis_x(cls):
        return cls(DB.XYZ.BasisX)

    @classmethod
    def basis_y(cls):
        return cls(DB.XYZ.BasisY)

    @classmethod
    def basis_z(cls):
        return cls(DB.XYZ.BasisZ)

    @property
    def unwrap(self):
        return self._rvt_obj

    def drop_z(self):
        """
        Creates a new PkXYZ with same x and y coordinates,
        but z = 0.
        """
        return PkXYZ.new(self.x, self.y, 0)

    def angle_on_plane_to(self, other, plane_normal):
        # type: (PkXYZ, PkXYZ) -> float
        return self._rvt_obj.AngleOnPlaneTo(other.unwrap, plane_normal.unwrap)

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


class PkDirectShape(PkElement):
    _RVT_TYPE = DB.DirectShape

    def __init__(self, rvt_geom_obj):
        # type: (DB.DirectShape) -> None
        self._validate_type(rvt_geom_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_geom_obj  # type: DB.DirectShape

    @property
    def unwrap(self):
        return self._rvt_obj

    def __str__(self):
        return (
            self.__class__.__name__
            + '[rvt_type <'
            + type(self._rvt_obj).__name__
            + '>]'
        )

    @classmethod
    def create_shape(cls, doc, category, geom_objects):
        # type: (PkDocument, PkCategory, Iterable[PkGeometryObject]) -> PkDirectShape # noqa
        """
        Creates DirectShape in the document
        from supplied geometry objects
        """
        d_shape = cls.create_element(doc, category)
        d_shape.set_shape(geom_objects)
        return d_shape

    @classmethod
    def create_element(cls, doc, category):
        # type: (PkDocument, PkCategory) -> PkDirectShape
        rvt_d_shape = DB.DirectShape.CreateElement(doc.unwrap,
                                                   category.id.unwrap)
        return cls(rvt_d_shape)

    def set_shape(self, geom_objects):
        # type: (Iterable[PkGeometryObject]) -> None
        rvt_geom_objecs = List[DB.GeometryObject](
            g.unwrap for g in geom_objects
        )

        self._rvt_obj.SetShape(rvt_geom_objecs)


class PkGeometryObject(BasePKWrapper):
    _RVT_TYPE = DB.GeometryObject

    def __init__(self, rvt_geom_obj):
        # type: (DB.GeometryObject) -> None
        self._validate_type(rvt_geom_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_geom_obj  # type: DB.GeometryObject

    @property
    def unwrap(self):
        return self._rvt_obj


class PkSolid(PkGeometryObject):
    _RVT_TYPE = DB.Solid

    def __init__(self, rvt_solid):
        # type: (DB.Solid) -> None
        self._validate_type(rvt_solid, self._RVT_TYPE)
        self._rvt_obj = rvt_solid  # type: DB.Solid

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def faces(self):
        return [PkFace(f) for f in self._rvt_obj.Faces]


class PkCuboid(PkSolid):
    _RVT_TYPE = DB.Solid

    def __init__(self):
        # type: () -> None
        raise NotImplementedError(
            'Initialization of {} is not allowed'
            .format(self.__class__.__name__)
        )

    def __str__(self):
        return (
            self.__class__.__name__
            + '[rvt_type <'
            + type(self._rvt_obj).__name__
            + '>]'
        )

    @classmethod
    def new_by_doagonal_corners(cls, corner_1, corner_2):
        # type: (PkXYZ, PkXYZ) -> PkCuboid
        corners = corner_1, corner_2
        cls._validate_diagonal_corners(corners)
        rvt_solid = cls._create_extrusion(corners)
        cuboid = cls.__new__(cls)
        cuboid._rvt_obj = rvt_solid
        return cuboid

    @classmethod
    def _validate_diagonal_corners(cls, corners):
        # type: (tuple[PkXYZ]) -> None

        for corner in corners:
            cls._validate_type(corner, PkXYZ)

        corner_1, corner_2 = corners
        dx = abs(corner_1.x - corner_2.x)
        dy = abs(corner_1.y - corner_2.y)
        dz = abs(corner_1.z - corner_2.z)

        COORD_NAMES = 'X', 'Y', 'Z'
        COORD_DELTAS = dx, dy, dz

        for name, delta in zip(COORD_NAMES, COORD_DELTAS):
            if delta < ui.pk_uiapp.app.short_curve_tolerance:
                raise pke.ValidationError(
                    'Corners are not diagonal: '
                    'Their {0} coordinate is same '
                    'or cuboid dimension towards {0} '
                    'is smaller than the minimum allowed length by Revit API.'
                    .format(name)
                )

    @classmethod
    def _create_extrusion(cls, corners):
        # type: (tuple[PkXYZ]) -> DB.Solid
        rectangle = cls._get_rectangle(corners)
        profile = List[DB.CurveLoop]()
        profile.Add(rectangle.unwrap)
        direction = DB.XYZ.BasisZ
        distance = abs(corners[0].z - corners[1].z)

        return DB.GeometryCreationUtilities.CreateExtrusionGeometry(
            profile,
            direction,
            distance
        )

    @classmethod
    def _get_rectangle(cls, corners):
        # type: (tuple[PkXYZ]) -> PkRectangularCurveLoop
        cube_min, cube_max = sorted(corners, key=itemgetter(2))
        bottom_left = cube_min
        top_right = PkXYZ.new(cube_max.x, cube_max.y, cube_min.z)
        plane = cls._get_xy_plane_at_point(bottom_left)

        return PkRectangularCurveLoop.new_by_plane_and_corners(
            plane,
            bottom_left,
            top_right
        )

    @classmethod
    def _get_xy_plane_at_point(cls, point):
        # type: (PkXYZ, PkXYZ) -> PkPlane
        x_dir = PkXYZ.basis_x()
        y_dir = PkXYZ.basis_y()
        return PkPlane.new_by_origin_and_basis(point, x_dir, y_dir)


class PkEdge(PkGeometryObject):
    _RVT_TYPE = DB.Edge

    def __init__(self, rvt_edge):
        # type: (DB.Edge) -> None
        self._validate_type(rvt_edge, self._RVT_TYPE)
        self._rvt_obj = rvt_edge  # type: DB.Edge

    @property
    def unwrap(self):
        return self._rvt_obj


class PkGeometryElement(PkGeometryObject):
    _RVT_TYPE = DB.GeometryElement

    def __init__(self, rvt_obj):
        # type: (DB.GeometryElement) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.GeometryElement

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_objects_of_type(self, pk_geom_obj_type):
        # type: (PkGeometryObject | type[T]) -> list[T]
        if not issubclass(pk_geom_obj_type, PkGeometryObject):
            raise pke.TypeValidationError(
                'expected {}, got {}'
                .format(PkGeometryObject, pk_geom_obj_type)
            )

        rvt_geom_objects = self._yeld_objects_of_type(
            self._rvt_obj,
            pk_geom_obj_type.get_rvt_obj_type()
        )

        return [PkGeometryObject.wrap(obj) for obj in rvt_geom_objects]

    def _yeld_objects_of_type(self, rvt_geom_elem, rvt_geom_obj_type):
        # type: (DB.GeometryElement, type[DB.GeometryObject]) -> Iterator[DB.GeometryObject] # noqa
        for geom_obj in rvt_geom_elem:
            if isinstance(geom_obj, DB.GeometryInstance):
                sub_geom_elem = geom_obj.GetInstanceGeometry()
                sub_objects = self._yeld_objects_of_type(
                    sub_geom_elem,
                    rvt_geom_obj_type
                )

                for sub_obj in sub_objects:
                    yield sub_obj

            if isinstance(geom_obj, rvt_geom_obj_type):
                yield geom_obj

    def get_transformed(self, transform):
        # type: (PkTransform) -> PkGeometryElement
        rvt_geom_elem = self._rvt_obj.GetTransformed(transform.unwrap)
        return PkGeometryElement(rvt_geom_elem)


class PkGeometryInstance(PkGeometryObject):
    _RVT_TYPE = DB.GeometryInstance

    def __init__(self, rvt_geom_instance):
        # type: (DB.GeometryInstance) -> None
        self._validate_type(rvt_geom_instance, self._RVT_TYPE)
        self._rvt_obj = rvt_geom_instance  # type: DB.GeometryInstance

    @property
    def unwrap(self):
        return self._rvt_obj


class PkMesh(PkGeometryObject):
    _RVT_TYPE = DB.Mesh

    def __init__(self, rvt_mesh):
        # type: (DB.Mesh) -> None
        self._validate_type(rvt_mesh, self._RVT_TYPE)
        self._rvt_obj = rvt_mesh  # type: DB.Mesh

    @property
    def unwrap(self):
        return self._rvt_obj


class PkPoint(PkGeometryObject):
    _RVT_TYPE = DB.Point

    def __init__(self, rvt_point):
        # type: (DB.Point) -> None
        self._validate_type(rvt_point, self._RVT_TYPE)
        self._rvt_obj = rvt_point  # type: DB.Point

    @property
    def unwrap(self):
        return self._rvt_obj


class PkPolyLine(PkGeometryObject):
    _RVT_TYPE = DB.PolyLine

    def __init__(self, rvt_poly_line):
        # type: (DB.PolyLine) -> None
        self._validate_type(rvt_poly_line, self._RVT_TYPE)
        self._rvt_obj = rvt_poly_line  # type: DB.PolyLine

    @property
    def unwrap(self):
        return self._rvt_obj


class PkProfile(PkGeometryObject):
    _RVT_TYPE = DB.Profile

    def __init__(self, rvt_profile):
        # type: (DB.Profile) -> None
        self._validate_type(rvt_profile, self._RVT_TYPE)
        self._rvt_obj = rvt_profile  # type: DB.Profile

    @property
    def unwrap(self):
        return self._rvt_obj


class PkFace(PkGeometryObject):
    _RVT_TYPE = DB.Face

    def __init__(self, rvt_face):
        # type: (DB.Face) -> None
        self._validate_type(rvt_face, self._RVT_TYPE)
        self._rvt_obj = rvt_face  # type: DB.Face

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_curve_intersection(self, pk_curve):
        # type: (PkCurve) -> PkFaceCurveIntersectionCheck
        return PkFaceCurveIntersectionCheck(self, pk_curve)


class PkBaseGeometryObjecstIntersectionCheck(BasePKObject):
    def _intersect_and_set_results(self, rvt_intersector, rvt_target_obj):
        # type: (callable, DB.GeometryObject) -> None
        """
        Intersects source geometry object with destination geometry object
        using intersection method of source object.
        """
        self._result_array = clr.Reference[DB.IntersectionResultArray]()  # type: DB.IntersectionResultArray # noqa
        self._comparison_result = rvt_intersector(rvt_target_obj, self._result_array)  # type: DB.SetComparisonResult # noqa

    @property
    def _has_intersection_results(self):
        # type: () -> bool
        # overwrite this method to follow subclass logic
        raise NotImplementedError('This is an abstract method!')

    @property
    def set_comparison_result(self):
        return self._comparison_result

    def get_intersection_results(self):
        # type: () -> list[PkIntersectionResult]
        if self._has_intersection_results:
            result_array_iterator = self._result_array.ForwardIterator()
            return [PkIntersectionResult(i) for i in result_array_iterator]
        return []


class PkCurveCurveIntersectionCheck(PkBaseGeometryObjecstIntersectionCheck):
    def __init__(self, pk_source_curve, pk_target_curve):
        # type: (PkCurve, PkCurve) -> None
        intersector = pk_source_curve.unwrap.Intersect
        self._intersect_and_set_results(intersector, pk_target_curve.unwrap)

    @property
    def _has_intersection_results(self):
        # type: () -> bool
        return self.has_intersections

    @property
    def has_intersections(self):
        # type: () -> bool
        return self._comparison_result == DB.SetComparisonResult.Overlap


class PkFaceCurveIntersectionCheck(PkBaseGeometryObjecstIntersectionCheck):
    def __init__(self, pk_face, pk_curve):
        # type: (PkFace, PkCurve) -> None
        intersector = pk_face.unwrap.Intersect
        self._intersect_and_set_results(intersector, pk_curve.unwrap)

    @property
    def _has_intersection_results(self):
        # type: () -> bool
        return self.has_intersections

    @property
    def has_intersections(self):
        # type: () -> bool
        """One or more intersections were encountered."""
        return self._comparison_result == DB.SetComparisonResult.Overlap

    @property
    def coincident(self):
        """The curve is coincident with the surface."""
        return self._comparison_result == DB.SetComparisonResult.Subset


class PkIntersectionResult(BasePKWrapper):
    _RVT_TYPE = DB.IntersectionResult

    def __init__(self, rvt_obj):
        # type: (DB.IntersectionResult) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.IntersectionResult

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def distance(self):
        # type: () -> float
        return self._rvt_obj.Distance

    @property
    def xyz_point(self):
        return PkXYZ(self._rvt_obj.XYZPoint)

    @property
    def uv_point(self):
        return PkUV(self._rvt_obj.UVPoint)

    @property
    def parameter(self):
        # type: () -> float
        return self._rvt_obj.Parameter


class PkCurve(PkGeometryObject):
    _RVT_TYPE = DB.Curve

    def __init__(self, rvt_curve):
        # type: (DB.Curve) -> None
        self._validate_type(rvt_curve, self._RVT_TYPE)
        self._rvt_obj = rvt_curve  # type: DB.Curve

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_end_point(self, index):
        # type: (int) -> PkXYZ
        return PkXYZ(self._rvt_obj.GetEndPoint(index))

    def get_intersection(self, pk_curve):
        # type: (PkCurve) -> PkCurveCurveIntersectionCheck
        return PkCurveCurveIntersectionCheck(self, pk_curve)

    def project(self, point):
        # type: (PkXYZ) -> PkIntersectionResult
        return PkIntersectionResult(self._rvt_obj.Project(point.unwrap))

    def compute_derivatives(self, parameter, normalized):
        # type: (float, bool) -> PkTransform
        rvt_transform = self._rvt_obj.ComputeDerivatives(parameter, normalized)
        return PkTransform(rvt_transform)

    @property
    def start(self):
        return self.get_end_point(0)

    @property
    def end(self):
        return self.get_end_point(1)

    @property
    def ends(self):
        return tuple(self.get_end_point(i) for i in (0, 1))


class PkArc(PkCurve):
    _RVT_TYPE = DB.Arc

    def __init__(self, rvt_line):
        # type: (DB.Arc) -> None
        self._validate_type(rvt_line, self._RVT_TYPE)
        self._rvt_obj = rvt_line  # type: DB.Arc

    def __str__(self):
        return (
            self.__class__.__name__
            + '('
            + str(self.start)
            + ', '
            + str(self.end)
            + ')'
        )

    @classmethod
    def by_plane_radius_angles(cls, plane, radius, start_angle, end_angle):
        # type: (PkPlane, float, float, float) -> PkArc
        return cls(DB.Arc.Create(plane.unwrap, radius, start_angle, end_angle))

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def direction(self):
        return PkXYZ(self._rvt_obj.Direction)


class PkLine(PkCurve):
    _RVT_TYPE = DB.Line

    def __init__(self, rvt_line):
        # type: (DB.Line) -> None
        self._validate_type(rvt_line, self._RVT_TYPE)
        self._rvt_obj = rvt_line  # type: DB.Line

    def __str__(self):
        return (
            self.__class__.__name__
            + '('
            + str(self.start)
            + ', '
            + str(self.end)
            + ')'
        )

    @classmethod
    def new_bound(cls, start, end):
        # type: (PkXYZ, PkXYZ) -> PkLine
        line = DB.Line.CreateBound(start.unwrap, end.unwrap)
        return cls(line)

    @classmethod
    def new_unbound(cls, start, direction):
        # type: (PkXYZ, PkXYZ) -> PkLine
        line = DB.Line.CreateUnbound(start.unwrap, direction.unwrap)
        return cls(line)

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def direction(self):
        return PkXYZ(self._rvt_obj.Direction)


class PkSurface(BasePKWrapper):
    _RVT_TYPE = DB.Surface

    def __init__(self, rvt_surface):
        # type: (DB.Surface) -> None
        self._validate_type(rvt_surface, self._RVT_TYPE)
        self._rvt_obj = rvt_surface  # type: DB.Surface

    @property
    def unwrap(self):
        return self._rvt_obj


class PkPlane(PkSurface):
    _RVT_TYPE = DB.Plane

    def __init__(self, rvt_plane):
        # type: (DB.Plane) -> None
        self._validate_type(rvt_plane, self._RVT_TYPE)
        self._rvt_obj = rvt_plane  # type: DB.Plane

    def __str__(self):
        return (
            self.__class__.__name__
            + '(Origin: '
            + str(self.origin)
            + ', Normal: '
            + str(self.normal)
            + ')'
        )

    @classmethod
    def new_by_origin_and_basis(cls, origin, basis_x, basis_y):
        # type: (PkXYZ, PkXYZ, PkXYZ) -> PkPlane
        return cls(
            DB.Plane.CreateByOriginAndBasis(
                origin.unwrap, basis_x.unwrap, basis_y.unwrap
            )
        )

    @classmethod
    def new_by_normal_and_origin(cls, normal, origin):
        # type: (PkXYZ, PkXYZ) -> PkPlane
        return cls(
            DB.Plane.CreateByNormalAndOrigin(normal.unwrap, origin.unwrap)
        )

    @classmethod
    def new_by_rvt_origin_and_basis(cls, origin, basis_x, basis_y):
        # type: (DB.XYZ, DB.XYZ, DB.XYZ) -> PkPlane
        return cls(DB.Plane.CreateByOriginAndBasis(origin, basis_x, basis_y))

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def origin(self):
        return PkXYZ(self.rvt_origin)

    @property
    def rvt_origin(self):
        # type: () -> DB.XYZ
        return self._rvt_obj.Origin

    @property
    def rvt_normal(self):
        return self._rvt_obj.Normal

    @property
    def normal(self):
        return PkXYZ(self.rvt_normal)

    @property
    def x_dir(self):
        return PkXYZ(self._rvt_obj.XVec)

    @property
    def y_dir(self):
        return PkXYZ(self._rvt_obj.YVec)

    @classmethod
    def xy(cls):
        return cls.new_by_origin_and_basis(
            PkXYZ.zero(), PkXYZ.basis_x(), PkXYZ.basis_y()
        )

    @classmethod
    def xz(cls):
        return cls.new_by_origin_and_basis(
            PkXYZ.zero(), PkXYZ.basis_x(), PkXYZ.basis_z()
        )

    @classmethod
    def yz(cls):
        return cls.new_by_origin_and_basis(
            PkXYZ.zero(), PkXYZ.basis_y(), PkXYZ.basis_z()
        )

    def is_point_on_plane(self, pk_point):
        # type: (PkXYZ) -> bool
        return self.nearest_point_to(pk_point) == pk_point

    def nearest_point_to(self, pk_xyz):
        # type: (PkXYZ) -> PkXYZ
        """Gets nearest point on plane to supplied point"""
        self._validate_type(pk_xyz, PkXYZ)
        normal = self.normal
        vec_to_orig = pk_xyz - self.origin
        signed_dist = normal.dot_product(vec_to_orig)
        return pk_xyz - (normal * signed_dist)

    def rvt_project(self, xyz):
        # type: (DB.XYZ) -> tuple[DB.UV, float]
        return self._rvt_obj.Project(xyz)

    def project(self, pk_xyz):
        # type: (PkXYZ) -> PkUV
        self._validate_type(pk_xyz, PkXYZ)
        u = (pk_xyz - self.origin).dot_product(self.x_dir)
        v = (pk_xyz - self.origin).dot_product(self.y_dir)
        return PkUV.new(u, v)

    def project_with_result(self, pk_xyz):
        # type: (PkXYZ) -> PkPointPlaneProjectionResult
        self._validate_type(pk_xyz, PkXYZ)
        return PkPointPlaneProjectionResult(self, pk_xyz)


class PkPointPlaneProjectionResult(BasePKObject):
    """Result of point projection on plane."""

    def __init__(self, plane, source_point):
        # type: (PkPlane, PkXYZ) -> None
        self._plane = plane
        self._source_xyz = source_point

    @property
    def plane(self):
        return self._plane

    @property
    def source_point(self):
        return self._source_xyz

    @property
    def translated_point(self):
        return self._plane.nearest_point_to(self._source_xyz)

    @property
    def projected_point(self):
        return self._plane.project(self._source_xyz)

    @property
    def transform(self):
        return PkTransform.new_translation(self.direction)

    @property
    def direction(self):
        return self.translated_point - self._source_xyz

    @property
    def distance(self):
        return self._source_xyz.distance_to(self.translated_point)


class PkCurveLoop(BasePKWrapper):
    _RVT_TYPE = DB.CurveLoop

    def __init__(self, rvt_curve_loop):
        # type: (DB.CurveLoop) -> None
        self._validate_type(rvt_curve_loop, self._RVT_TYPE)
        self._rvt_obj = rvt_curve_loop  # type: DB.CurveLoop

    def __str__(self):
        return (
            self.__class__.__name__
            + '('
            + str(self.num_of_curves)
            + ' curves)'
        )

    def __getitem__(self, key):
        # type: (int) -> PkCurveLoop
        return self.curves[key]

    def __iter__(self):
        return self._get_curves_generator().__iter__()

    @property
    def num_of_curves(self):
        # type: () -> int
        return self._rvt_obj.NumberOfCurves()

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def has_plane(self):
        # type: () -> bool
        return self._rvt_obj.HasPlane()

    @property
    def is_rectangular(self):
        # type: () -> bool
        if not self.has_plane:
            return False

        plane = self.get_rvt_plane()
        return self._rvt_obj.IsRectangular(plane)

    def get_rvt_plane(self):
        return self._rvt_obj.GetPlane()

    def get_plane(self):
        rvt_plane = self._rvt_obj.GetPlane()
        if rvt_plane is not None:
            return PkPlane(rvt_plane)

    @property
    def curves(self):
        # type: () -> tuple[PkCurveLoop]
        return tuple(self._get_curves_generator())

    def _get_curves_generator(self):
        # type: () -> Generator[PkCurve]
        return (PkCurve.wrap(rvt_curve) for rvt_curve in self._rvt_obj)


class PkRectangularCurveLoop(PkCurveLoop):
    _RVT_TYPE = DB.CurveLoop

    def __init__(self, rvt_curve_loop):
        # type: (DB.CurveLoop) -> None
        self._validate_type(rvt_curve_loop, self._RVT_TYPE)
        self._validate_rectangular(rvt_curve_loop)
        self._rvt_obj = rvt_curve_loop  # type: DB.CurveLoop

    def _validate_rectangular(self, loop):
        # type: (DB.CurveLoop) -> None
        if not loop.HasPlane():
            raise pke.ValidationError(
                'Curve loop has no plane, thus can not be rectangular.'
            )

        plane = loop.GetPlane()
        if not loop.IsRectangular(plane):
            raise pke.ValidationError('Curve is not rectangular.')

    @classmethod
    def new_by_plane_and_corners(cls, plane, corner_1, corner_2):
        # type: (PkPlane, PkXYZ, PkXYZ) -> PkRectangularCurveLoop
        cls._validate_type(plane, PkPlane)
        corners = corner_1, corner_2
        cls._validate_diagonal_corners(plane, corners)
        rvt_rectangle = cls._build_rvt_rectangle(plane, corners)
        return cls(rvt_rectangle)

    @classmethod
    def _build_rvt_rectangle(cls, plane, corners):
        # type: (PkPlane, tuple[PkXYZ]) -> DB.CurveLoop

        bottom_left, top_right = sorted(plane.project(c) for c in corners)

        top_left = PkUV.new(bottom_left.u, top_right.v)
        bottom_right = PkUV.new(top_right.u, bottom_left.v)

        ordered_corners = bottom_left, top_left, top_right, bottom_right

        model_corners = tuple(
            c.as_pk_xyz_on_plane(plane) for c in ordered_corners
        )

        rvt_loop = DB.CurveLoop()
        for end_1, end_2 in pki.circular_pairwise(model_corners):
            rvt_line = DB.Line.CreateBound(end_1.unwrap, end_2.unwrap)
            rvt_loop.Append(rvt_line)

        return rvt_loop

    @classmethod
    def _validate_diagonal_corners(cls, plane, corners):
        # type: (PkPlane, tuple[PkXYZ]) -> None
        for corner in corners:
            cls._validate_type(corner, PkXYZ)
            cls._validate_point_on_plane(corner, plane)

        corner_1, corner_2 = corners
        axes = plane.x_dir, plane.y_dir
        diagonal = PkLine.new_bound(corner_1, corner_2).direction
        if any(diagonal.is_parallel(a) for a in axes):
            raise pke.ValidationError(
                'Corners are not diagonal in relation to plane. '
                'Make sure they don\'t form a line, '
                'orthogonal to any of the plane axes.'
            )

        for corner_1_coord, corner_2_coord in zip(*corners)[:-1]:
            distance = abs(corner_1_coord - corner_2_coord)
            if distance < ui.pk_uiapp.app.short_curve_tolerance:
                raise pke.ValidationError(
                    'Some side of the rectangle is smaller than '
                    'the minimum allowed length by Revit API.'
                )

    @classmethod
    def _validate_point_on_plane(cls, point, plane):
        # type: (PkXYZ, PkPlane) -> None
        if not plane.is_point_on_plane(point):
            raise pke.ValidationError(
                'Point {} is not on plane {}.'
                .format(point, plane)
            )


class PkTransform(BasePKWrapper):
    _RVT_TYPE = DB.Transform

    def __init__(self, rvt_transform):
        # type: (DB.Transform) -> None
        self._validate_type(rvt_transform, self._RVT_TYPE)
        self._rvt_obj = rvt_transform  # type: DB.Transform

    def __mul__(self, other):
        # type: (PkTransform) -> PkTransform
        return self.multiply(other)

    def __rmul__(self, other):
        # type: (PkTransform) -> PkTransform
        return self.__mul__(other)

    def __eq__(self, other):
        # type: (PkTransform) -> bool
        """Checks transforms equality using `almost_equal()` method
        with the default Revit tolerance.
        """
        return self.almost_equal(other)

    def __ne__(self, other):
        # type: (PkTransform) -> bool
        return not self.__eq__(other)

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def identity(cls):
        return cls(DB.Transform.Identity)

    @classmethod
    def new_translation(cls, pk_xyz):
        # type: (PkXYZ) -> PkTransform
        return cls(DB.Transform.CreateTranslation(pk_xyz.unwrap))

    @classmethod
    def new_reflection(cls, plane):
        # type: (PkPlane) -> Self
        return cls(DB.Transform.CreateReflection(plane.unwrap))

    def of_point(self, pk_xyz):
        # type: (PkXYZ) -> PkXYZ
        return PkXYZ(self._rvt_obj.OfPoint(pk_xyz.unwrap))

    def multiply(self, other):
        # type: (PkTransform) -> PkTransform
        return self._wrap_to_self(self._rvt_obj.Multiply(other.unwrap))

    def inverse(self):
        # type: () -> PkTransform
        return self._wrap_to_self(self._rvt_obj.Inverse)

    def almost_equal(self, other):
        # type: (PkTransform) -> bool
        return self._rvt_obj.AlmostEqual(other.unwrap)

    @property
    def origin(self):
        return PkXYZ(self._rvt_obj.Origin)

    @property
    def basis_x(self):
        return PkXYZ(self._rvt_obj.BasisX)

    @basis_x.setter
    def basis_x(self, value):
        # type: (PkXYZ) -> None
        self._rvt_obj.BasisX = value.unwrap

    @property
    def basis_y(self):
        return PkXYZ(self._rvt_obj.BasisY)

    @basis_y.setter
    def basis_y(self, value):
        # type: (PkXYZ) -> None
        self._rvt_obj.BasisY = value.unwrap

    @property
    def basis_z(self):
        return PkXYZ(self._rvt_obj.BasisZ)

    @basis_z.setter
    def basis_z(self, value):
        # type: (PkXYZ) -> None
        self._rvt_obj.BasisZ = value.unwrap


class PkCurveElement(PkElement):
    _RVT_TYPE = DB.CurveElement

    def __init__(self, rvt_curve_element):
        # type: (DB.CurveElement) -> None
        self._validate_type(rvt_curve_element, self._RVT_TYPE)
        self._rvt_obj = rvt_curve_element  # type: DB.CurveElement

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def sketch_plane(self):
        return PkSketchPlane(self._rvt_obj.SketchPlane)

    @property
    def geometry_curve(self):
        return PkCurve(self._rvt_obj.GeometryCurve)


class PkModelCurve(PkCurveElement):
    _RVT_TYPE = DB.ModelCurve

    def __init__(self, rvt_model_curve):
        # type: (DB.ModelCurve) -> None
        self._validate_type(rvt_model_curve, self._RVT_TYPE)
        self._rvt_obj = rvt_model_curve  # type: DB.ModelCurve

    @property
    def unwrap(self):
        return self._rvt_obj


class PkModelLine(PkModelCurve):
    _RVT_TYPE = DB.ModelLine

    def __init__(self, rvt_model_line):
        # type: (DB.ModelLine) -> None
        self._validate_type(rvt_model_line, self._RVT_TYPE)
        self._rvt_obj = rvt_model_line  # type: DB.ModelLine

    @property
    def unwrap(self):
        return self._rvt_obj


class PkDetailCurve(PkCurveElement):
    _RVT_TYPE = DB.DetailCurve

    def __init__(self, rvt_model_curve):
        # type: (DB.DetailCurve) -> None
        self._validate_type(rvt_model_curve, self._RVT_TYPE)
        self._rvt_obj = rvt_model_curve  # type: DB.DetailCurve

    @property
    def unwrap(self):
        return self._rvt_obj


class PkDetailLine(PkCurveElement):
    _RVT_TYPE = DB.DetailLine

    def __init__(self, rvt_model_curve):
        # type: (DB.DetailLine) -> None
        self._validate_type(rvt_model_curve, self._RVT_TYPE)
        self._rvt_obj = rvt_model_curve  # type: DB.DetailLine

    @property
    def unwrap(self):
        return self._rvt_obj


class PkDetailArc(PkCurveElement):
    _RVT_TYPE = DB.DetailArc

    def __init__(self, rvt_model_curve):
        # type: (DB.DetailArc) -> None
        self._validate_type(rvt_model_curve, self._RVT_TYPE)
        self._rvt_obj = rvt_model_curve  # type: DB.DetailArc

    @property
    def unwrap(self):
        return self._rvt_obj


class PkSketchPlane(PkElement):
    _RVT_TYPE = DB.SketchPlane

    def __init__(self, rvt_sketch_plane):
        # type: (DB.SketchPlane) -> None
        self._validate_type(rvt_sketch_plane, self._RVT_TYPE)
        self._rvt_obj = rvt_sketch_plane  # type: DB.SketchPlane

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_plane(self):
        return PkPlane(self._rvt_obj.GetPlane())

    @classmethod
    def create(cls, doc, pk_elem):
        # type: (PkDocument, PkDatumPlane | PkPlane | PkReference) -> PkSketchPlane  # noqa
        if isinstance(pk_elem, PkDatumPlane):
            return cls(DB.SketchPlane.Create(doc.unwrap, pk_elem.id.unwrap))
        return cls(DB.SketchPlane.Create(doc.unwrap, pk_elem.unwrap))


class PkCurveElement(PkElement):
    _RVT_TYPE = DB.CurveElement

    def __init__(self, rvt_curve_elem):
        # type: (DB.CurveElement) -> None
        self._validate_type(rvt_curve_elem, self._RVT_TYPE)
        self._rvt_obj = rvt_curve_elem  # type: DB.CurveElement

    @property
    def unwrap(self):
        return self._rvt_obj


class PkRenderNode(BasePKWrapper):
    _RVT_TYPE = DB.RenderNode

    def __init__(self, obj):
        # type: (DB.RenderNode) -> None
        self._validate_type(obj, self._RVT_TYPE)
        self._rvt_obj = obj  # type: DB.RenderNode

    @property
    def unwrap(self):
        return self._rvt_obj


class PkTextNode(PkRenderNode):
    _RVT_TYPE = DB.TextNode

    def __init__(self, txt_node):
        # type: (DB.TextNode) -> None
        self._validate_type(txt_node, self._RVT_TYPE)
        self._rvt_obj = txt_node  # type: DB.TextNode

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_formatted_text(self):
        return PkFormattedText(self._rvt_obj.GetFormattedText())

    @property
    def text(self):
        return self._rvt_obj.Text

    @text.setter
    def text(self, vaule):
        # type: (str) -> None
        formatted_text = self.get_formatted_text()
        formatted_text.set_plain_text(vaule)


class PkFormattedText(BasePKWrapper):
    _RVT_TYPE = DB.FormattedText

    def __init__(self, fromatted_txt):
        # type: (DB.FormattedText) -> None
        self._validate_type(fromatted_txt, self._RVT_TYPE)
        self._rvt_obj = fromatted_txt  # type: DB.FormattedText

    @property
    def unwrap(self):
        return self._rvt_obj

    def set_plain_text(self, text):
        # type: (str) -> None
        self._rvt_obj.SetPlainText(text)


class PkCategory(BasePKWrapper):
    _RVT_TYPE = DB.Category

    def __init__(self, cat):
        # type: (DB.Category) -> None
        self._validate_type(cat, self._RVT_TYPE)
        self._rvt_obj = cat  # type: DB.Category

    @property
    def unwrap(self):
        return self._rvt_obj

    def __eq__(self, other):
        # type: (PkCategory) -> bool
        """Meaningless for categories from different projects"""
        return self.id == other.id

    def __ne__(self, other):
        # type: (PkCategory) -> bool
        """Meaningless for categories from different projects"""
        return not self.__eq__(other)

    @classmethod
    def by_bic(cls, doc, built_in_category):
        # type: (PkDocument, DB.BuiltInCategory) -> PkCategory
        rvt_cat = DB.Category.GetCategory(doc.unwrap, built_in_category)
        return cls(rvt_cat)

    @property
    def id(self):
        return PkElementId(self._rvt_obj.Id)

    @property
    def name(self):
        return self._rvt_obj.Name

    @property
    def is_bic(self):
        # type: () -> bool
        return self._rvt_obj.Id < DB.ElementId.InvalidElementId

    @property
    def as_bic(self):
        # type: () -> DB.BuiltInCategory
        BICS = DB.BuiltInCategory
        if self.is_bic:
            name = BICS.GetName(BICS, self.id.value)
            if name is not None:
                return BICS.Parse(BICS, name)

        return BICS.INVALID


class PkElementId(BasePKWrapper):
    _RVT_TYPE = DB.ElementId

    def __init__(self, elem_id):
        # type: (DB.ElementId) -> None
        self._validate_type(elem_id, self._RVT_TYPE)
        self._rvt_obj = elem_id  # type: DB.ElementId

    def __str__(self):
        return (
            self.__class__.__name__
            + '[rvt_type <'
            + type(self._rvt_obj).__name__
            + '> (id: '
            + str(self.value)
            + ')]'
        )

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def by_bic(cls, built_in_category):
        # type: (DB.BuiltInCategory) -> PkElementId
        rvt_elem_id = DB.ElementId(built_in_category)
        return cls(rvt_elem_id)

    @classmethod
    def by_bip(cls, built_in_parameter):
        # type: (DB.BuiltInParameter) -> PkElementId
        rvt_elem_id = DB.ElementId(built_in_parameter)
        return cls(rvt_elem_id)

    @classmethod
    def by_int(cls, integer_value):
        # type: (int) -> PkElementId
        rvt_elem_id = DB.ElementId(integer_value)
        return cls(rvt_elem_id)

    @property
    def value(self):
        # type: () -> int | Int64
        if hasattr(self._rvt_obj, 'IntegerValue'):
            # prior to Revit 2024
            return self._rvt_obj.IntegerValue
        return self._rvt_obj.Value

    @property
    def is_invalid(self):
        return self._rvt_obj == DB.ElementId.InvalidElementId

    def __lt__(self, other):
        # type: (PkElementId) -> bool
        raise self._rvt_obj < other._rvt_obj

    def __eq__(self, other):
        # type: (PkElementId) -> bool
        return self._rvt_obj == other._rvt_obj

    def __ne__(self, other):
        # type: (PkElementId) -> bool
        return not self.__eq__(other)

    def __gt__(self, other):
        # type: (PkElementId) -> bool
        return not self.__lt__(other) and self.__ne__(other)

    def __le__(self, other):
        # type: (PkElementId) -> bool
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        # type: (PkElementId) -> bool
        return not self.__lt__(other)

    def get_element(self, doc):
        # type: (PkDocument) -> PkElement
        return doc.get_element(self)

    @classmethod
    def get_invalid_element_id(cls):
        return cls(DB.ElementId.InvalidElementId)


class PkLinkOrHostElementId(BasePKWrapper):
    _RVT_TYPE = DB.LinkElementId

    def __init__(self, elem):
        # type: (DB.LinkElementId) -> None
        self._validate_type(elem, self._RVT_TYPE)
        self._rvt_obj = elem  # type: DB.LinkElementId

    @property
    def unwrap(self):
        return self._rvt_obj

    def __eq__(self, other):
        # type: (PkLinkOrHostElementId) -> bool
        return self._rvt_obj == other._rvt_obj

    def __ne__(self, other):
        # type: (PkLinkOrHostElementId) -> bool
        return not self.__eq__(other)

    @property
    def id(self):
        if self.is_linked:
            return PkElementId(self._rvt_obj.LinkedElementId)
        return PkElementId(self._rvt_obj.HostElementId)

    @property
    def is_linked(self):
        return not self.link_instance_id.is_invalid

    @property
    def link_instance_id(self):
        return PkElementId(self._rvt_obj.LinkInstanceId)


class PkReference(BasePKWrapper):
    _RVT_TYPE = DB.Reference

    def __init__(self, ref):
        # type: (DB.Reference) -> None
        self._validate_type(ref, self._RVT_TYPE)
        self._rvt_obj = ref  # type: DB.Reference

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_linked_doc(self, host_doc):
        # type: (PkDocument) -> PkDocument
        link_instance_id = self.element_id
        link_instance = host_doc.get_element(
            link_instance_id)  # type: PkRevitLinkInstance
        return link_instance.get_link_document()

    def get_linked_elem(self, host_doc):
        # type: (PkDocument) -> PkElement
        linked_doc = self.get_linked_doc(host_doc)
        return linked_doc.get_element(self.linked_element_id)

    def get_element(self, doc):
        # type: (PkDocument) -> PkElement
        return doc.get_element(self.element_id)

    @property
    def element_id(self):
        return PkElementId(self._rvt_obj.ElementId)

    @property
    def linked_element_id(self):
        return PkElementId(self._rvt_obj.LinkedElementId)

    @property
    def global_point(self):
        rvt_point = self._rvt_obj.GlobalPoint
        if rvt_point is not None:
            return PkXYZ(rvt_point)


class PkHostObject(PkElement):
    _RVT_TYPE = DB.HostObject

    def __init__(self, rvt_obj):
        # type: (DB.HostObject) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.HostObject

    @property
    def unwrap(self):
        return self._rvt_obj


class PkMEPCurve(PkHostObject):
    _RVT_TYPE = DB.MEPCurve

    def __init__(self, rvt_obj):
        # type: (DB.MEPCurve) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.MEPCurve

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def connector_manager(self):
        return PkConnectorManager(self._rvt_obj.ConnectorManager)

    @property
    def diameter(self):
        # type: () -> float | None
        return self._rvt_obj.Diameter


class PkMEPSystem(PkElement):
    _RVT_TYPE = DB.MEPSystem

    def __init__(self, rvt_obj):
        # type: (DB.MEPSystem) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.MEPSystem

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def base_equipment(self):
        rvt_fam_instance = self._rvt_obj.BaseEquipment
        if rvt_fam_instance is not None:
            return PkFamilyInstance.wrap(rvt_fam_instance)


class PkLocation(BasePKWrapper):
    _RVT_TYPE = DB.Location

    def __init__(self, rvt_obj):
        # type: (DB.Location) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Location

    @property
    def unwrap(self):
        return self._rvt_obj

    def move(self, translation):
        # type: (PkXYZ) -> bool
        """Attempts to move. Returns attempt result."""
        return self._rvt_obj.Move(translation.unwrap)

    def rotate(self, axis, angle):
        # type: (PkLine, float) -> bool
        """Attempts to rotate. Returns attempt result."""
        return self._rvt_obj.Rotate(axis.unwrap, angle)


class PkLocationCurve(PkLocation):
    _RVT_TYPE = DB.LocationCurve

    def __init__(self, rvt_obj):
        # type: (DB.LocationCurve) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.LocationCurve

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def curve(self):
        rvt_curve = self._rvt_obj.Curve
        if rvt_curve is not None:
            return PkCurve.wrap(rvt_curve)


class PkLocationPoint(PkLocation):
    _RVT_TYPE = DB.LocationPoint

    def __init__(self, rvt_obj):
        # type: (DB.LocationPoint) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.LocationPoint

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def point(self):
        return PkXYZ(self._rvt_obj.Point)

    @point.setter
    def point(self, new_location):
        # type: (PkXYZ) -> None
        self._rvt_obj = new_location.unwrap

    @property
    def rotation(self):
        # type: () -> float
        """
        This property is not supported for some elements, such as
        AssemblyInstances, Groups, ModelText, Room, and SpotDimensions.
        """
        return self._rvt_obj.Rotation


class PkMEPModel(BasePKWrapper):
    _RVT_TYPE = DB.MEPModel

    def __init__(self, rvt_obj):
        # type: (DB.MEPModel) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.MEPModel

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def connector_manager(self):
        rvt_connector_manager = self._rvt_obj.ConnectorManager
        if rvt_connector_manager is not None:
            return PkConnectorManager(rvt_connector_manager)


class PkConnectorManager(BasePKWrapper):
    _RVT_TYPE = DB.ConnectorManager

    def __init__(self, rvt_obj):
        # type: (DB.ConnectorManager) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ConnectorManager

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def connectors(self):
        return [
            PkConnector(c) for c in self._rvt_obj.Connectors
        ]

    @property
    def unused_connectors(self):
        return [
            PkConnector(c) for c in self._rvt_obj.UnusedConnectors
        ]

    def lookup(self, index):
        # type: (int) -> PkConnector
        rvt_connector = self._rvt_obj.Lookup(index)
        return PkConnector(rvt_connector)


class PkConnector(BasePKWrapper):
    _RVT_TYPE = DB.Connector

    def __init__(self, rvt_obj):
        # type: (DB.Connector) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.Connector
        self._uuid = uuid.uuid4()

    @property
    def unwrap(self):
        return self._rvt_obj

    @property
    def owner(self):
        # type: () -> PkElement
        return PkElement.wrap(self._rvt_obj.Owner)

    def connect_to(self, other):
        # type: (Self) -> None
        self._rvt_obj.ConnectTo(other.unwrap)

    def is_connected_to(self, other):
        # type: (Self) -> bool
        return self._rvt_obj.IsConnectedTo(other.unwrap)

    @property
    def is_connected(self):
        # type: () -> bool
        return self._rvt_obj.IsConnected

    @property
    def origin(self):
        return PkXYZ(self._rvt_obj.Origin)

    @property
    def all_refs(self):
        return [PkConnector(conn) for conn in self._rvt_obj.AllRefs]

    @property
    def id(self):
        # type: () -> int
        return self._rvt_obj.Id

    @property
    def domain(self):
        # type: () -> DB.Domain
        return self._rvt_obj.Domain

    @property
    def is_electrical_domain(self):
        # type: () -> bool
        return self.domain == DB.Domain.DomainElectrical

    @property
    def connector_type(self):
        # type: () -> DB.ConnectorType
        return self._rvt_obj.ConnectorType

    @property
    def is_conn_type_end(self):
        # type: () -> bool
        return self.connector_type == DB.ConnectorType.End

    @property
    def uuid(self):
        """UUID generated at the initialization of PkConnector"""
        return self._uuid

    def get_coords_id(self):
        """Generates tuple of integers based on connector coordinates and id"""
        coords_id = [int(c * 1000) for c in self.origin]
        coords_id.append(self.id)
        return tuple(coords_id)


class PkElementTransformUtils(BasePKWrapper):
    _RVT_TYPE = DB.ElementTransformUtils

    def __init__(self, rvt_obj):
        # type: (DB.Connector) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.ElementTransformUtils

    @property
    def unwrap(self):
        return self._rvt_obj

    @classmethod
    def copy_element(cls, doc, elem_id, translation):
        # type: (PkDocument, PkElementId, PkXYZ) -> list[PkElement]
        copied_ids = DB.ElementTransformUtils.CopyElement(
            doc.unwrap,
            elem_id.unwrap,
            translation.unwrap
        )
        return [PkElementId(id).get_element(doc) for id in copied_ids]

    @classmethod
    def mirror_element(cls, doc, elem_id, plane):
        # type: (PkDocument, PkElementId, PkPlane) -> None
        """Mirrors Element removing the original"""
        DB.ElementTransformUtils.MirrorElement(
            doc.unwrap,
            elem_id.unwrap,
            plane.unwrap
        )

    @classmethod
    def move_element(cls, doc, elem_id, translation):
        # type: (PkDocument, PkElementId, PkXYZ) -> None
        DB.ElementTransformUtils.MoveElement(
            doc.unwrap,
            elem_id.unwrap,
            translation.unwrap
        )

    @classmethod
    def rotate_element(cls, doc, elem_id, line, angle):
        # type: (PkDocument, PkElementId, PkLine, float) -> None
        DB.ElementTransformUtils.RotateElement(
            doc.unwrap,
            elem_id.unwrap,
            line.unwrap,
            angle
        )

    @classmethod
    def copy_elems_to_view(cls,
                           source_view,
                           elems,
                           dest_view,
                           transform=None,
                           opts=None):
        # type: (PkView, list[PkElement], PkView, PkTransform, PkCopyPasteOptions) -> list[PkElement]  # noqa

        if transform is None:
            transform = PkTransform.identity()

        if opts is None:
            opts = PkCopyPasteOptions(DB.CopyPasteOptions())

        rvt_elem_ids = List[DB.ElementId]()

        for elem in elems:
            rvt_elem_ids.Add(elem.id.unwrap)

        copied_rvt_ids = DB.ElementTransformUtils.CopyElements(
            source_view.unwrap,
            rvt_elem_ids,
            dest_view.unwrap,
            transform.unwrap,
            opts.unwrap
        )
        return [
            PkElementId(id).get_element(dest_view.doc) for id in copied_rvt_ids
        ]


class PkCopyPasteOptions(BasePKWrapper):
    _RVT_TYPE = DB.CopyPasteOptions

    def __init__(self, rvt_obj):
        # type: (DB.CopyPasteOptions) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.CopyPasteOptions

    @property
    def unwrap(self):
        return self._rvt_obj


class PkPlanViewRange(BasePKWrapper):
    _RVT_TYPE = DB.PlanViewRange

    def __init__(self, rvt_obj):
        # type: (DB.PlanViewRange) -> None
        self._validate_type(rvt_obj, self._RVT_TYPE)
        self._rvt_obj = rvt_obj  # type: DB.PlanViewRange

    @property
    def unwrap(self):
        return self._rvt_obj

    def get_level_id(self, plan_view_plane):
        # type: (DB.PlanViewPlane) -> PkElementId
        return PkElementId(self._rvt_obj.GetLevelId(plan_view_plane))

    def set_level_id(self, plan_view_plane, lvl_id):
        # type: (DB.PlanViewPlane, PkElementId) -> None
        self._rvt_obj.SetLevelId(plan_view_plane, lvl_id.unwrap)

    @classmethod
    def current(cls):
        """They did it instead of Enum. So did I..."""
        return PkElementId(DB.PlanViewRange.Current)

    @classmethod
    def level_above(cls):
        """They did it instead of Enum. So did I..."""
        return PkElementId(DB.PlanViewRange.LevelAbove)

    @classmethod
    def level_below(cls):
        """They did it instead of Enum. So did I..."""
        return PkElementId(DB.PlanViewRange.LevelBelow)

    @classmethod
    def unlimited(cls):
        """They did it instead of Enum. So did I..."""
        return PkElementId(DB.PlanViewRange.Unlimited)

    def set_offset(self, plan_view_plane, offset):
        # type: (DB.PlanViewPlane, float) -> None
        self._rvt_obj.SetOffset(plan_view_plane, offset)
