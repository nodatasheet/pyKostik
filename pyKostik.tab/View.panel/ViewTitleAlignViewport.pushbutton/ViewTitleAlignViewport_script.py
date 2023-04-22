"""Aligns View Titles with their Viewports
  and adjusts View Title line lengths to text.
    Alignment options:
        Bottom Left
        Bottom Center
        Bottom Right
        Top Left
        Top Center
        Top Right
"""

from pyrevit import revit, DB, HOST_APP, forms, script, coreutils

doc = revit.doc   # type: DB.Document
active_sheet = HOST_APP.active_view  # type: DB.ViewSheet


class UnitsConverter(object):
    def __init__(self, doc):
        # type: (DB.Document) -> None
        self._doc = doc
        self._doc_units = doc.GetUnits()
        self._revit_version = int(HOST_APP.version)

    def length_to_internal_units(self, length):
        # type: (float) -> float
        """Converts length from document units to Revit's internal units."""
        return DB.UnitUtils.ConvertToInternalUnits(length, self._uiunits)

    def length_from_internal_units(self, length):
        # type: (float) -> float
        """Converts length from Revit's internal units to document units."""
        return DB.UnitUtils.ConvertFromInternalUnits(length, self._uiunits)

    @property
    def _uiunits(self):
        if self._revit_version < 2021:
            return self._get_ui_units_2020()
        return self._get_uiunits_2021()

    def _get_ui_units_2020(self):
        return self._doc_units.GetFormatOptions(
            DB.UnitType.UT_Length).DisplayUnits

    def _get_uiunits_2021(self):
        return self._doc_units.GetFormatOptions(
            DB.SpecTypeId.Length).GetUnitTypeId()


def get_viewport_name(viewport):
    # type: (DB.Viewport) -> str

    detail_num = get_param_as_str(viewport,
                                  DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER)

    title_on_sheet = get_param_as_str(viewport,
                                      DB.BuiltInParameter.VIEW_DESCRIPTION)
    if title_on_sheet:
        return '{}: {}'.format(detail_num, title_on_sheet)

    view_name = get_param_as_str(viewport, DB.BuiltInParameter.VIEW_NAME)
    if view_name:
        return '{}: {}'.format(detail_num, view_name)

    return viewport.Name


def get_param_as_str(elem, built_in_param):
    param = elem.get_Parameter(built_in_param)
    if param:
        return param.AsString()


ask_align_all = forms.alert(
    msg=('Align all viewport title-blocks in current sheet?\n\n'
         'Click "No" if want to select specific viewports'),
    yes=True,
    no=True
)

if ask_align_all:
    viewports = [doc.GetElement(id) for id in active_sheet.GetAllViewports()]
else:
    with forms.WarningBar(title='Select viewports'):
        picked_elems = revit.pick_elements_by_category(
            DB.BuiltInCategory.OST_Viewports
        )
        if picked_elems:
            viewports = picked_elems
        else:
            script.exit()

skipped_viewport_names = []
unskipped_viewports = []
for vp in viewports:
    if vp.Rotation != coreutils.get_enum_none(DB.ViewportRotation):
        skipped_viewport_names.append(get_viewport_name(vp))
    else:
        unskipped_viewports.append(vp)

if skipped_viewport_names:
    ask_skip_viewports = forms.alert(
        msg=('Some viewports are rotated (see in details).\n'
             'Alignment is not supported for such kind of viewports. \n\n'
             'Skip them and continue with the rest?'),
        yes=True,
        cancel=True,
        expanded='\n'.join(sorted(skipped_viewport_names))
    )
    if ask_skip_viewports:
        viewports = unskipped_viewports
    else:
        script.exit()

position = 'Bottom Center'
units_converter = UnitsConverter(doc)
vertical_offset = units_converter.length_to_internal_units(0)
adjust_length = True

with revit.TransactionGroup('Align view title with viewport'):
    if adjust_length:
        with revit.Transaction('Reset length'):
            for vp in viewports:
                vp.LabelLineLength = 0.0

        with revit.Transaction('Match title line length'):
            for vp in viewports:
                label_outline = vp.GetLabelOutline()
                label_length = (label_outline.MaximumPoint.X
                                - label_outline.MinimumPoint.X)
                vp.LabelLineLength = label_length
                rvt_label_length = \
                    units_converter.length_from_internal_units(label_length)

    with revit.Transaction('Move to viewport zero'):
        for vp in viewports:
            vp.LabelOffset = DB.XYZ()

    with revit.Transaction('Align'):
        for vp in viewports:
            vp_outline = vp.GetBoxOutline()
            label_outline = vp.GetLabelOutline()

            vp_min = vp_outline.MinimumPoint
            vp_max = vp_outline.MaximumPoint
            label_min = label_outline.MinimumPoint
            label_max = label_outline.MaximumPoint

            vp_width = vp_max.X - vp_min.X
            vp_height = vp_max.Y - vp_min.Y
            label_width = label_max.X - label_min.X
            label_height = label_max.Y - label_min.Y

            label_left_part = vp_min.X - label_min.X
            label_top_part = label_max.Y - vp_min.Y

            if "Left" in position:
                x = label_left_part

            if "Center" in position:
                x = label_left_part + (vp_width - label_width) / 2

            if "Right" in position:
                x = vp_width - label_width + label_left_part

            if "Top" in position:
                y = vp_height + label_height - label_top_part + vertical_offset

            if "Bottom" in position:
                y = - (vertical_offset + label_top_part)

            vp.LabelOffset = DB.XYZ(x, y, 0)
