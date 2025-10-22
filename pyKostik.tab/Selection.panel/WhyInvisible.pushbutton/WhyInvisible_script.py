from pyrevit import DB, UI, HOST_APP, revit, script, forms

import reports
import checks as ch
import source_view as sv
import invisible_element as ie


doc = HOST_APP.doc  # type: DB.Document
active_view = HOST_APP.active_view  # type: DB.View
output = script.get_output()
selection = revit.get_selection()

if not selection:
    script.exit()


elem = ie.wrap_to_invisible_element(selection.first)
view = sv.wrap_to_source_view(active_view)
report = reports.Report(elem)

checks = [
    ch.ElementIsVisible(elem, view),
    ch.ElementNotHidden(elem, view),
    ch.ElementCategoryNotHidden(elem, view),
    ch.ElementPhaseStatusDisplayed(elem, view),
    ch.ElementPhaseStatusNotOverridden(elem, view),
    ch.ViewNotInTempHiddenMode(view),
    ch.ElementInsideCrop(elem, view),
    ch.ElementNotInDesignOption(elem),
    ch.ElementNotHiddenByViewFilter(elem, view),
    ch.ElementInPlanViewRange(elem, view),
    ch.ElementInSectionDepthRange(elem, view),
    ch.ElementInSectionDepthCueing(elem, view),
    ch.ElementInsideSectionBox(elem, view),
    ch.ElementWorksetNotClosed(elem),
    ch.ElementWorksetNotHiddenInView(elem, view),
    ch.ViewTagShownInThisOrIntersectingViews(elem, view),
    ch.ViewScaleNotCoarserViewTag(elem, view),
    ch.ViewTagDisciplineMatchesView(elem, view)
]  # type: list[ch.Check]

for check in checks:
    if check.worth_checking:
        report.add(check)

report.run_checks()
report.print_results()
