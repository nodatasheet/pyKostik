from System.Collections.Generic import List

from pyrevit import DB, HOST_APP, revit, script, forms
from pykostik import exceptions as pke

SCOPE_BOX_BIC = DB.BuiltInCategory.OST_VolumeOfInterest
TRANSACTION_NAME = 'Set Scope Box Name To Parameters'

doc = HOST_APP.doc  # type: DB.Document
active_view = HOST_APP.active_view
logger = script.get_logger()
selection = revit.get_selection()


class LinesNotChainedError(pke.PyKostikException):
    pass


class LineWrap(object):
    def __init__(self, line):
        # type: (DB.Line) -> None
        self._line = line
        self._start = PointWrap(self._line.GetEndPoint(0))
        self._end = PointWrap(self._line.GetEndPoint(1))

    def __str__(self):
        return '{} [{}, {}]'.format(
            type(self).__name__,
            str(self.start),
            str(self.end)
        )

    def _are_numbers_close(self, a, b, rel_tol=1e-09, abs_tol=0.0):
        # type: (float, float, float, float) -> bool
        """A function for testing approximate equality of two numbers.
        Same as math.isclose in Python v3.5 (and newer)
        https://www.python.org/dev/peps/pep-0485
        """
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    @classmethod
    def new(cls, start, end):
        # type: (DB.XYZ, DB.XYZ) -> LineWrap
        return cls(DB.Line.CreateBound(start, end))

    def new_reversed(self):
        return self.new(self._end.xyz, self._start.xyz)

    def is_connected_to(self, other):
        # type: (LineWrap) -> bool
        return any(
            (self._start == other.start,
             self._start == other.end,
             self._end == other.start,
             self._end == other.end)
        )

    def is_parallel_to(self, xyz):
        # type: (DB.XYZ) -> bool
        dot_prod = self.direction.DotProduct(xyz)
        return self._are_numbers_close(abs(dot_prod), 1)

    @property
    def direction(self):
        return self._line.Direction

    @property
    def line(self):
        return self._line

    @property
    def length(self):
        return self._line.Length

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end


class PointWrap(object):
    def __init__(self, xyz):
        # type: (DB.XYZ) -> None
        self._xyz = xyz

    def __str__(self):
        return str(self.approx_coords)

    def __eq__(self, other):
        # type: (PointWrap) -> bool
        return self._xyz.IsAlmostEqualTo(other.xyz)

    def __ne__(self, other):
        # type: (PointWrap) -> bool
        return not self == other

    @property
    def approx_coords(self):
        return tuple(
            round(coord, 9) for coord in (self.x, self.y, self.z)
        )

    @property
    def x(self):
        return self._xyz.X

    @property
    def y(self):
        return self._xyz.Y

    @property
    def z(self):
        return self._xyz.Z

    @property
    def xyz(self):
        return self._xyz


class LineGroups(object):
    """Groups of lines grouped by connectivity"""

    def __init__(self, line_wraps):
        # type: (list[LineWrap]) -> None
        self._line_wraps = line_wraps
        self._groups = self._group_by_connectivity()

    @classmethod
    def group_to_chain(cls, line_wraps):
        # type: (list[LineWrap]) -> list[LineWrap]
        if len(line_wraps) == 1:
            return line_wraps

        chain = [line_wraps[0]]
        rest = line_wraps[1:]
        counter = 0
        initial_qty = len(rest)
        while rest:
            last_in_chain = chain[-1]
            for reversed_index, line in enumerate(reversed(rest)):
                if line.is_connected_to(last_in_chain):
                    if line.start != last_in_chain.end:
                        line = line.new_reversed()
                    chain.append(line)
                    actual_index = len(rest) - reversed_index - 1
                    rest.pop(actual_index)
                    break
            counter += 1
            if counter > initial_qty:
                raise LinesNotChainedError
        return chain

    def _group_by_connectivity(self):
        # type: () -> list[list[LineWrap]]
        """Groups lines by their connectivity."""
        lines_dict = {i: v for i, v in enumerate(self._line_wraps)}
        neighbors = self._get_neighbors(lines_dict)
        merged = self._merge_touching_sets(neighbors)
        return [[lines_dict[k] for k in group] for group in merged]

    def _get_neighbors(self, lines_dict):
        # type: (dict) -> list[set[dict.key]]
        """Gets all neighbors for each curve
            as list of sets of dictionary keys"""
        all_neighbours = []
        for i in lines_dict:
            sub_neighbours = {i}
            for j in lines_dict:
                line = lines_dict[i]  # type: LineWrap
                if j != i and line.is_connected_to(lines_dict[j]):
                    sub_neighbours.add(j)
            all_neighbours.append(sub_neighbours)
        return all_neighbours

    def _merge_touching_sets(self, sets):
        # type: (list[set]) -> list[set]
        """Merges sets with common elements.
            Source: https://stackoverflow.com/a/9400562
        """
        new_group = []
        while len(new_group) != len(sets):
            new_group, sets = sets, []
            for set1 in new_group:
                for set2 in sets:
                    if not set1.isdisjoint(set2):
                        set2.update(set1)
                        break
                else:
                    sets.append(set1)
        return sets

    @property
    def groups(self):
        return self._groups


class ScopeBoxGeometry(object):

    def __init__(self, geometry_element):
        # type: (DB.GeometryElement) -> None
        self._geometry_elem = geometry_element
        geom_objects = list(self._geometry_elem)
        self._line_wraps = self._get_line_wraps(geom_objects)

        if not self._line_wraps:
            raise pke.InvalidOperationException(
                'Scope Box Element does not have any lines'
            )

    def _get_line_wraps(self, geom_objects):
        # type: (list[DB.GeometryObject]) -> list[LineWrap]
        line_wraps = []
        for geom in geom_objects:
            if isinstance(geom, DB.Line):
                line_wraps.append(LineWrap(geom))
        return line_wraps

    def get_solid(self):
        # type: () -> DB.Solid
        vertical_line_wrap = self._get_first_vertical_line_wrap()
        profile_loops = self._get_profile_loops()
        return DB.GeometryCreationUtilities.CreateExtrusionGeometry(
            profile_loops,
            vertical_line_wrap.direction,
            vertical_line_wrap.length
        )

    def _get_first_vertical_line_wrap(self):
        for line_wrap in self._line_wraps:
            if line_wrap.is_parallel_to(DB.XYZ.BasisZ):
                return line_wrap

    def _get_profile_loops(self):
        # type: () -> List[DB.CurveLoop]
        bottom_rectagle = self._get_bottom_rectangle()
        profile_loops = List[DB.CurveLoop]()
        profile_loops.Add(bottom_rectagle)
        return profile_loops

    def _get_bottom_rectangle(self):
        bottom_lines = self._get_bottom_lines()
        chained_lines = LineGroups.group_to_chain(bottom_lines)
        curve_loop = DB.CurveLoop()
        for line_wrap in chained_lines:
            curve_loop.Append(line_wrap.line)
        return curve_loop

    def _get_bottom_lines(self):
        horizontal_line_wraps = self._get_horizontal_line_wraps()
        line_groups = LineGroups(horizontal_line_wraps).groups

        if len(line_groups) != 2:
            raise pke.InvalidOperationException(
                'Horizontal lines were not properly grouped'
                ' (num of groups != 2)'
            )

        first_group, second_group = line_groups

        if first_group[0].start.z < second_group[0].start.z:
            return first_group
        return second_group

    def _get_horizontal_line_wraps(self):
        return [
            line for line in self._line_wraps
            if not line.is_parallel_to(DB.XYZ.BasisZ)
        ]


class IntersectedElement(object):
    def __init__(self, element):
        # type: (DB.Element) -> None
        self._elem = element

    def set_param_value(self, param_name, value):
        # type: (str, str) -> None
        param = self._lookup_parameter(param_name)

        if param.StorageType != DB.StorageType.String:
            raise pke.FailedAttempt('Parameter type is not text')

        set_attempt = param.Set(value)
        if not set_attempt or param.AsString() != value:
            raise pke.FailedAttempt('Failed setting parameter value')

    def _lookup_parameter(self, param_name):
        # type: (str) -> DB.Parameter
        param = self._elem.LookupParameter(param_name)
        if param is not None:
            return param

        elem_type = doc.GetElement(self._elem.GetTypeId())
        type_param = elem_type.LookupParameter(param_name)
        if type_param is not None:
            return type_param

        raise pke.FailedAttempt('Parameter does not exist')

    @property
    def family_and_type(self):
        # type: () -> str | None
        param = self._elem.get_Parameter(
            DB.BuiltInParameter.ELEM_FAMILY_AND_TYPE_PARAM
        )
        if param is not None:
            return param.AsValueString()

    @property
    def name(self):
        # type: () -> str
        return self._elem.Name

    @property
    def id(self):
        return self._elem.Id


class Report(object):

    def __init__(self, param_name):
        # type: (str) -> None
        self._param_name = param_name
        self._succeed_scope_boxes = []  # type: list[ScopeBoxReport]
        self._failed_scope_boxes = []  # type: list[ScopeBoxReport]
        self._empty_scope_boxes = []  # type: list[ScopeBoxReport]
        self._all_scope_boxes = []  # type: list[ScopeBoxReport]

    def add(self, scope_box_report):
        # type: (ScopeBoxReport) -> None
        if scope_box_report.is_empty:
            self._empty_scope_boxes.append(scope_box_report)

        elif scope_box_report.qty_failed:
            self._failed_scope_boxes.append(scope_box_report)

        else:
            self._succeed_scope_boxes.append(scope_box_report)

        self._all_scope_boxes.append(scope_box_report)

    def show_report(self):
        ask_txt = self._prepare_ask_report_txt()
        print_opts = self._prepare_peport_print_opts()

        ask_print_report = forms.alert(
            msg=ask_txt,
            warn_icon=bool(self.qty_failed or self.qty_empty),
            options=print_opts
        )

        if ask_print_report:
            self._print_selected_report(ask_print_report)

    def _print_selected_report(self, ask_print_report):
        if ask_print_report == ReportPrintOptions.print_full:
            self.print_full()

        elif ask_print_report == ReportPrintOptions.print_empty:
            self.print_empty()

        elif ask_print_report in [ReportPrintOptions.print_failed,
                                  ReportPrintOptions.print_empty_and_failed]:
            self.print_empty_and_failed()

    def _prepare_peport_print_opts(self):
        basic_opts = ReportPrintOptions.basic_options

        if self.qty_empty and self.qty_failed:
            return basic_opts + [ReportPrintOptions.print_empty_and_failed]

        if self.qty_failed:
            return basic_opts + [ReportPrintOptions.print_failed]

        if self.qty_empty:
            return basic_opts + [ReportPrintOptions.print_empty]

        return basic_opts

    def _prepare_ask_report_txt(self):
        ask_txt = 'Completed {} Scope Boxes.\n'.format(self.qty_all)

        if self.qty_empty:
            ask_txt += (
                '{} of them do(es) not intersect any element.\n'
                .format(self.qty_empty)
            )

        if self.qty_failed:
            ask_txt += (
                '{} of them have some elements '
                'that failed setting the parameter.\n'
                .format(self.qty_failed)
            )

        ask_txt += '\nShow report?'

        return ask_txt

    def print_empty(self):
        self._print_description()

        sorted_empty = sorted(self._empty_scope_boxes, key=lambda x: x.name)
        for scope_box in sorted_empty:
            scope_box.print_description()

    def print_full(self):
        self._print_description()

        sorted_all = sorted(self._all_scope_boxes, key=lambda x: x.name)
        for scope_box in sorted_all:
            scope_box.print_description()
            scope_box.print_all()

    def _print_description(self):
        output = script.get_output()
        output.print_md(
            '# Result of setting Scope Box names '
            'to intersected elements parameter "{}"'
            .format(self._param_name)
        )

    def print_empty_and_failed(self):
        self._print_description()

        empty_and_failed = self._empty_scope_boxes + self._failed_scope_boxes
        empty_and_failed.sort(key=lambda x: x.name)
        for scope_box in empty_and_failed:
            scope_box.print_description()
            scope_box.print_failed()

    @property
    def qty_succeed(self):
        return len(self._succeed_scope_boxes)

    @property
    def qty_failed(self):
        return len(self._failed_scope_boxes)

    @property
    def qty_all(self):
        return len(self._all_scope_boxes)

    @property
    def qty_empty(self):
        return len(self._empty_scope_boxes)


class ScopeBoxReport(object):

    def __init__(self, scope_box_name):
        # type: (str) -> None
        self._name = scope_box_name
        self._output = script.get_output()
        self._succeed_elems = []  # type: list[ElemetReport]
        self._failed_elems = []  # type: list[ElemetReport]

    def add(self, report_element):
        # type: (ElemetReport) -> None
        if report_element.error_msg is None:
            self._succeed_elems.append(report_element)
        else:
            self._failed_elems.append(report_element)

    def print_description(self):
        self._output.print_md('<br>')
        prefix = ':warning: ' if self.is_empty else ''
        self._output.print_md(
            '## {}Scope Box "{}" intersected elements processing: '
            '{} total, {} succeed, {} failed.'
            .format(
                prefix,
                self._name,
                self.qty_all,
                self.qty_succeed,
                self.qty_failed
            )
        )

    def print_all(self):
        if self.qty_succeed:
            self.print_succeed()
        if self.qty_failed:
            self.print_failed()

    def print_succeed(self):
        self._output.print_md('### Succeed elements')
        sorted_succeed = sorted(self._succeed_elems, key=lambda x: x.name)
        for rep_elem in sorted_succeed:
            txt = self._get_basic_report_txt(rep_elem)
            self._output.print_md(txt)

    def print_failed(self):
        self._output.print_md('### :warning: Failed elements')
        sorted_failed = sorted(self._failed_elems, key=lambda x: x.name)
        for rep_elem in sorted_failed:
            txt = self._get_basic_report_txt(rep_elem)
            self._output.print_md(txt + ': ' + rep_elem.error_msg)

    def _get_basic_report_txt(self, rep_elem):
        # type: (ElemetReport) -> str
        return '- {} {}'.format(
            rep_elem.name,
            self._output.linkify(rep_elem.id)
        )

    @property
    def is_empty(self):
        return self.qty_all == 0

    @property
    def name(self):
        return self._name

    @property
    def qty_succeed(self):
        return len(self._succeed_elems)

    @property
    def qty_failed(self):
        return len(self._failed_elems)

    @property
    def qty_all(self):
        return self.qty_succeed + self.qty_failed


class ElemetReport(object):
    _error_msg = None

    def __init__(self, intersec_elem):
        # type: (IntersectedElement) -> None
        self._elem = intersec_elem

    @property
    def name(self):
        return self._elem.family_and_type or self._elem.name

    @property
    def id(self):
        return self._elem.id

    @property
    def error_msg(self):
        # type: () -> str | None
        return self._error_msg

    @error_msg.setter
    def error_msg(self, txt):
        # type: (str) -> None
        self._error_msg = txt


class ReportPrintOptions(object):
    do_not_print = 'Do Not Show'
    print_full = 'Show Full Report'
    print_empty = 'Show Empty Scope Boxes'
    print_failed = 'Show Failed Elements Of Failed Scope Boxes'
    print_empty_and_failed = 'Show Failed And Empty Scope Boxes'
    basic_options = [
        do_not_print,
        print_full,
    ]


class ScopeBoxWrap(object):
    def __init__(self, scope_box):
        # type: (DB.Element) -> None
        self._scope_box_elem = scope_box
        self._doc = scope_box.Document
        self._intersec_elems = self._get_intersected_elems()

    def _get_intersected_elems(self):
        collector = self._get_intersec_elems_collector()
        return [IntersectedElement(elem) for elem in collector]

    def _get_intersec_elems_collector(self):
        outline = self._get_outline()
        solid = self._get_solid()
        bb_intersec_filter = DB.BoundingBoxIntersectsFilter(outline)
        solid_intersec_filter = DB.ElementIntersectsSolidFilter(solid)

        return (
            DB.FilteredElementCollector(self._doc)
            .WhereElementIsNotElementType()
            .WhereElementIsViewIndependent()
            .WherePasses(bb_intersec_filter)
            .WherePasses(solid_intersec_filter)
        )

    def _get_outline(self):
        # type: () -> DB.Outline
        active_view = self._doc.ActiveView
        bb = self._scope_box_elem.get_BoundingBox(active_view)
        return DB.Outline(bb.Min, bb.Max)

    def _get_solid(self):
        geom_opts = DB.Options()
        scope_box_geom_elem = self._scope_box_elem.get_Geometry(geom_opts)
        scope_box_geom = ScopeBoxGeometry(scope_box_geom_elem)
        return scope_box_geom.get_solid()

    @property
    def name(self):
        return str(self._scope_box_elem.Name)

    @property
    def intersected_elems(self):
        return self._intersec_elems


class FailureCatcher(DB.IFailuresPreprocessor):
    def __init__(self, ids_to_skip):
        # type: (list[DB.Element]) -> None
        self._ids_to_skip = ids_to_skip

    def PreprocessFailures(self, failuresAccessor):
        # type: (DB.FailuresAccessor) -> None
        group_failures = DB.BuiltInFailures.GroupFailures
        FAILURES_TO_CANCEL = [
            group_failures.AtomTouchedNotAllowed,
            group_failures.AtomTouchedNotAllowedDelete,
            group_failures.AtomViolationWhenMultiPlacedInstances
        ]

        failures = failuresAccessor.GetFailureMessages()

        for failure in failures:
            failure = failure   # type: DB.FailureMessageAccessor
            failure_id = failure.GetFailureDefinitionId()

            if failure_id in FAILURES_TO_CANCEL:
                self._ids_to_skip.extend(failure.GetFailingElementIds())

        if self._ids_to_skip:
            return DB.FailureProcessingResult.ProceedWithRollBack

        return DB.FailureProcessingResult.Continue


class FailureCatchingTransaction():

    def __init__(self, doc, name, ids_to_skip):
        """If this transaction catches group-related failure
        that can not be ignored,
        it will roll back and feed caught element ids.
        """
        _doc = doc
        self._trans = DB.Transaction(_doc, name)
        flr_hndlr_opts = self._trans.GetFailureHandlingOptions()
        flr_hndlr_opts = flr_hndlr_opts.SetClearAfterRollback(True)
        flr_hndlr_opts = flr_hndlr_opts.SetForcedModalHandling(False)
        catcher = FailureCatcher(ids_to_skip)
        flr_hndlr_opts = flr_hndlr_opts.SetFailuresPreprocessor(catcher)
        self._trans.SetFailureHandlingOptions(flr_hndlr_opts)

    def __enter__(self):
        self._trans.Start()
        return self

    def __exit__(self, exception, exception_value, traceback):
        if exception:
            self._trans.RollBack()
        else:
            try:
                self._trans.Commit()
            except Exception as errmsg:
                self._trans.RollBack()
                logger.error('Error in Transaction Commit. '
                             'Rolling back changes. | %s', errmsg)


def set_param_and_prepare_report(scope_boxes, param_name, ids_to_skip=[]):
    # type: (list[ScopeBoxWrap], str, list[DB.ElementId]) -> Report
    report = Report(param_name)
    past_intersec_elem_ids = set()

    for scope_box in scope_boxes:
        scope_box_report = ScopeBoxReport(scope_box.name)

        for intersec_elem in scope_box.intersected_elems:
            elem_report = ElemetReport(intersec_elem)

            try:
                intersec_elem_id = intersec_elem.id

                if intersec_elem_id in ids_to_skip:
                    raise pke.FailedAttempt(
                        'Changing this parameter is forbidden'
                        ' outside of group edit mode'
                    )

                if intersec_elem_id in past_intersec_elem_ids:
                    raise pke.FailedAttempt(
                        'Element already intersecting another scope box. '
                        'This scope box name will be skipped.'
                    )

                intersec_elem.set_param_value(param_name, scope_box.name)
                past_intersec_elem_ids.add(intersec_elem_id)

            except Exception as err:
                elem_report.error_msg = str(err)

            scope_box_report.add(elem_report)
        report.add(scope_box_report)

    return report


def are_all_of_bic(elements, bic):
    # type: (list[DB.Element], DB.BuiltinCategory) -> bool
    for elem in elements:
        if not hasattr(elem, 'Category'):
            return False
        if elem.Category is None:
            return False
        if elem.Category.Id != DB.ElementId(bic):
            return False
    return True


scope_box_elems = []
current_selection = selection.elements
if current_selection:
    if are_all_of_bic(current_selection, SCOPE_BOX_BIC):
        ask_use_selected = forms.alert(
            msg='Use Selected Scope Box(es)?',
            yes=True,
            no=True
        )
        if ask_use_selected:
            scope_box_elems = current_selection

if not scope_box_elems:
    with forms.WarningBar(title='Select Scope Boxes'):
        scope_box_elems = revit.pick_elements_by_category(SCOPE_BOX_BIC)

if not scope_box_elems:
    script.exit()

scope_boxes = [ScopeBoxWrap(elem) for elem in scope_box_elems]

param_name = forms.ask_for_string(
    prompt='Input name of the parameter that will be filled in',
    default='BOM_MOD ID'
)

if not param_name:
    script.exit()

ids_to_skip = []  # type: list[DB.ElementId]

with FailureCatchingTransaction(doc=doc,
                                name=TRANSACTION_NAME,
                                ids_to_skip=ids_to_skip):

    report = set_param_and_prepare_report(scope_boxes, param_name)

if ids_to_skip:
    with revit.Transaction(TRANSACTION_NAME):

        report = set_param_and_prepare_report(
            scope_boxes,
            param_name,
            ids_to_skip
        )

report.show_report()
