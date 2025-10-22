# encoding: utf-8

from Autodesk.Revit import DB
from pyrevit.coreutils import applocales

import source_view as sv
import invisible_element as ie
import check_exceptions as che


class Check(object):
    _SYMBOL_CHECKMARK = ':white_heavy_check_mark:'
    _SYMBOL_CROSSMARK = ':cross_mark:'
    _SYMBOL_EYES = ':eyes:'
    _SYMBOL_SAD = ':frowning_face:'
    _SYMBOL_WARNING = ':warning:'
    _title = ''
    _descr = ''
    _result = ''
    _hint = ''
    _symbol = ''
    _error_trace = ''
    _passed = None
    _failed_with_error = None

    def check(self):
        raise NotImplementedError('abstract method')

    def _set_default_good_result(self):
        self._symbol = self._SYMBOL_CHECKMARK
        self._result = self._default_good_result
        self._passed = True
        self._failed_with_error = False

    def set_check_error(self, err_txt=None, formatted_trace=None):
        # type: (str, str) -> None
        self._symbol = self._SYMBOL_WARNING
        self._passed = False
        self._failed_with_error = True

        if err_txt is not None:
            err_txt = ' (' + err_txt + ')'

        self._result = self._result_default_error.format(err_txt)

        if formatted_trace is not None:
            self._error_trace = formatted_trace

    @property
    def passed(self):
        return self._passed

    @property
    def failed_with_error(self):
        # type: () -> bool
        return self._failed_with_error

    @property
    def title(self):
        return self._title

    @property
    def description(self):
        return self._descr

    @property
    def result(self):
        return self._result

    @property
    def hint(self):
        return self._hint

    @property
    def symbol(self):
        return self._symbol

    @property
    def error_trace(self):
        return self._error_trace

    @property
    def _default_good_result(self):
        # type: () -> str
        DEFAULT = 'No problems found'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Проблем не найдено'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_failed_getting_elem_bb(self):
        # type: () -> str
        DEFAULT = 'Failed getting element bounding box'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Не получилось найти границы элемента'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_default_error(self):
        # type: () -> str
        DEFAULT = 'Failed to check due to error{}.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Не удалось проверить из-за внутренней ошибки{}.'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_cant_check_without_bb(self):
        # type: () -> str
        DEFAULT = (
            'On some reason failed getting element bounding box. '
            'Thus, can not perform this check. '
            'You have to check it manually or see if other checks indicate it.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'По какой-то причине не удалось получить границы элемента. '
                'Следовательно, нет возможности сделать эту проверку. '
                'Проверьте эту проблему вручную '
                'или посмотрите, указывают ли на нее другие проверки.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        # type: () -> bool
        """Default is True. False decision is made by subclass."""
        return True


class ElementIsVisible(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view

    def check(self):
        if self._elem.is_visible(self._view):
            self._symbol = self._SYMBOL_EYES
            self._result = self._result_elem_is_visible
            self._hint = self._hint_try_zooming
        else:
            self._passed = False
            self._symbol = self._SYMBOL_SAD
            self._result = self._result_elem_is_invisible

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Check if Revit can see the element'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Проверяем, видит ли Revit элемент'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_visible(self):
        # type: () -> str
        DEFAULT = 'Revit thinks it can see the element'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Revit думает, что он видит элемент'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_invisible(self):
        # type: () -> str
        DEFAULT = 'Revit does not see the element as well'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Revit тоже не видит элемент'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_try_zooming(self):
        # type: () -> str
        DEFAULT = (
            'Try zooming to element '
            '(press on magnifier icon next to id).'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Попробуйте приблизиться к элементу '
                '(нажать на значок лупы возле его id).'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementNotHidden(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if self._elem.is_hidden(self._view):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_hidden
            self._hint = self._hint_unhide

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is not permanently hidden in view'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент не скрыт на виде'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = 'Using right-click -> Hide in View -> Elements'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Через правую кнопку мыши -> '
                'Скрыть при просмотре -> Элементы'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_hidden(self):
        # type: () -> str
        DEFAULT = 'It was hidden'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Он был скрыт'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_unhide(self):
        # type: () -> str
        DEFAULT = 'Unhide element in "Reveal Hidden Elements" mode'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Нажмите "Показать элемент" '
                'в режиме "Показать скрытые элементы"'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementCategoryNotHidden(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        elem = self._elem
        cat = elem.cat

        if isinstance(elem, ie.ViewTag):
            cat = elem.get_ui_cat()

        cat_id = cat.Id

        if cat_id is None:
            self._passed = False
            self._symbol = self._SYMBOL_WARNING
            self._result = self._failed_getting_cat
            return

        if self._view.is_category_hidden(cat_id):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_cat_is_hidden.format(cat.Name)

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element\'s category is not hidden in view'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Категория элемента не скрыта на виде'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = 'In visibility / Graphics settings'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Через окно "Переопределения видимости/графики"'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_cat_is_hidden(self):
        # type: () -> str
        DEFAULT = 'Category "{}" was hidden'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Категория "{}" была скрыта'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _failed_getting_cat(self):
        # type: () -> str
        DEFAULT = 'Failed getting element category'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Не получилось получить категорию элемента'
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementPhaseStatusDisplayed(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        view_phase_id = self._view.get_view_phase_id()
        elem_status = self._elem.get_phase_status(view_phase_id)

        if elem_status == DB.ElementOnPhaseStatus.Future:
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._phase_status_future
            return

        if self._view.is_phase_status_hidden(elem_status):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._phase_status_hidden.format(elem_status)

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element\'s phase status is displayed in view'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Статус стадии элемента отображается на виде'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _phase_status_future(self):
        # type: () -> str
        DEFAULT = (
            'Element is in future phase in the timeline. '
            'Such elements are not displayed in view.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Элемент находится будущей стадии шкалы времени.'
                'Такие элементы не отображаются на виде.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _phase_status_hidden(self):
        # type: () -> str
        DEFAULT = (
            'Element is in phase status "{}" to view, '
            'which is set as "Not Displayed" in current view filter'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Элемент находится в статусе стадии "{}" к данному виду, '
                'которое установлено как "Не отображается" '
                'в текущем фильтре стадий вида.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        return self._elem.has_phases


class ElementPhaseStatusNotOverridden(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        view_phase_id = self._view.get_view_phase_id()
        elem_status = self._elem.get_phase_status(view_phase_id)

        if self._view.is_phase_status_overridden(elem_status):
            self._passed = False
            self._symbol = self._SYMBOL_WARNING
            self._result = self._phase_status_overridden.format(elem_status)

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element\'s phase status graphics are not overridden'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Графика статуса стадии элемента не переопределена'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _phase_status_overridden(self):
        # type: () -> str
        DEFAULT = (
            'Element is in phase status "{}" to view, '
            'which graphics are overridden in current view filter. '
            'These graphics overrides can cause element not being visible. '
            'You have to check it manually.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Элемент находится в статусе стадии "{}" к данному виду, '
                'у которого переопределены настройки графики '
                'в текущем фильтре стадий вида. '
                'Эти настройки графики могли привести к тому, '
                'что элемент не видно. '
                'Вам придётся это проверить вручную.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        return self._elem.has_phases


class ViewNotInTempHiddenMode(Check):
    def __init__(self, view):
        # type: (sv.SourceView) -> None
        self._view = view
        self._set_default_good_result()

    def check(self):
        if self._view.is_in_temp_hidden_mode:
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_view_in_this_mode
            self._hint = self._hint_reset_view_mode

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'View is not in temporary hide/isolate mode'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Вид не в режиме "Временное скрытие/изоляция"'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = 'Element or it\'s category could be temporary hidden'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Элемент или его категория '
                'могут быть временно скрыты на виде'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_view_in_this_mode(self):
        # type: () -> str
        DEFAULT = 'View is in this mode'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Вид в этом режиме'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_reset_view_mode(self):
        # type: () -> str
        DEFAULT = (
            'Reset temporary hide/isolate mode. '
            'Maybe you can find the element.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Выключите режим "Временное скрытие/изоляция". '
                'Возможно, элемент появится.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementWorksetNotClosed(Check):
    def __init__(self, elem):
        # type: (ie.InvisibleElement) -> None
        self._elem = elem
        self._title = 'Element\'s workset is not closed'
        self._descr = 'for docs in worksharing mode'
        self._set_default_good_result()

    def check(self):
        if self._elem.doc.IsWorkshared and self._elem.is_workset_closed:
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            workset_name = self._elem.workset_name
            self._result = self._result_workset_is_closed.format(workset_name)
            self._hint = self._hint_open_workset

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element\'s workset is not closed'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент не находится в закрытом рабочем наборе'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = 'For projects in worksharing mode'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Для проектов в режиме совместной работы с рабочими наборами'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_workset_is_closed(self):
        # type: () -> str
        DEFAULT = 'Workset "{}" is closed'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Рабочий набор "{}" закрыт'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_open_workset(self):
        # type: () -> str
        DEFAULT = 'Go to worksets and open it'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Зайдите в "Рабочие наборы" и откройте его'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if self._elem.doc.IsWorkshared:
            return True

        return False


class ElementWorksetNotHiddenInView(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if not self._view.is_workset_visible(self._elem.workset_id):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = (
                self._result_workset_is_hidden
                .format(self._elem.workset_name)
            )
            self._hint = self._hint_turned_off

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element\'s workset is not hidden in view'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент не находится в скрытом рабочем наборе'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = 'For projects in worksharing mode'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Для проектов в режиме совместной работы с рабочими наборами'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_workset_is_hidden(self):
        # type: () -> str
        DEFAULT = 'Workset "{}" is not visible in view'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Рабочий набор {} скрыт в виде'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_turned_off(self):
        # type: () -> str
        DEFAULT = (
            'It could be turned off globally in worksets '
            'or in view settings'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Он мог быть выключен глобально в настройках рабочих наборов '
                'или на вкладке "рабочие наборы" окна '
                '"Переопределение видимости/графики" для данного вида'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if self._elem.doc.IsWorkshared:
            return True

        return False


class ElementInsideCrop(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if not self._view.is_crop_box_active:
            self._result = self._result_crop_is_off
            return

        elem = self._elem
        elem_bb = elem.get_bb(self._view)

        if elem.is_annotation_category:
            if not self._view.is_anno_crop_active:
                self._result = self._result_anno_crop_is_off
                return

            if elem_bb is None:
                self._passed = False
                self._symbol = self._SYMBOL_WARNING
                self._result = self._result_failed_getting_anno_bb
                self._hint = self._hint_turn_off_anno_crop
                return

            if not self._view.anno_crop_contains_bb(elem_bb):
                self._passed = False
                self._symbol = self._SYMBOL_CROSSMARK
                self._result = self._result_elem_is_outside_anno_crop
                return

            return

        if elem_bb is None:
            self._passed = None
            self._symbol = self._SYMBOL_WARNING
            self._result = self._result_failed_getting_elem_bb
            self._hint = self._hint_cant_check_without_bb
            return

        if not self._view.crop_contains_bb(elem_bb):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_outside_crop
            return

        if not self._view.is_crop_shape_rectangle:
            self._passed = False
            self._symbol = self._SYMBOL_WARNING
            self._result = self._result_crop_not_rectang

        if self._view.is_crop_shape_split:
            self._passed = False
            self._symbol = self._SYMBOL_WARNING
            self._result = self._result_crop_split

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is inside the view crop'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент в пределах области обрезки вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_crop_is_off(self):
        # type: () -> str
        DEFAULT = 'Crop box is turned off'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Область обрезки вида выключена'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_anno_crop_is_off(self):
        # type: () -> str
        DEFAULT = 'Annotation crop is turned off'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Область обрезки аннотаций выключена'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_outside_crop(self):
        # type: () -> str
        DEFAULT = 'Element is outside of the view crop.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится за пределами обрезки вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_outside_anno_crop(self):
        # type: () -> str
        DEFAULT = 'Element is outside of the annotation crop.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится за пределами обрезки аннотаций'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_failed_getting_anno_bb(self):
        # type: () -> str
        DEFAULT = 'Failed getting annotation borders'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Не получилось найти границы аннотации'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_turn_off_anno_crop(self):
        # type: () -> str
        DEFAULT = (
            'Currently can not get borders of invisible annotation. '
            'Thus, can not define if it is inside the annotation crop. '
            'You can try turning off annotation crop and see if it appears.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'На данный момент мы не можем получить границы аннотации, '
                'если она невидима. Следовательно, нет возможности проверить, '
                'находится ли она внутри подрезки аннотаций,'
                'Вы можете попробовать отключить границы аннотации '
                'и посмотреть, появится ли она.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_crop_not_rectang(self):
        # type: () -> str
        DEFAULT = (
            'View crop shape is not rectangular or rotated.'
            'Even if element is inside the bounding box of view crop, '
            'we don\'t check that it is inside crop polygon (yet).'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Подрезка вида не прямоугольной формы или повёрнута. '
                'Даже если элемент находится внутри подрезки вида, '
                'мы на данный момент не можем этого проверить '
                'для непрямоугольных форм.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_crop_split(self):
        # type: () -> str
        DEFAULT = (
            'View crop is split. '
            'We don\'t check every split crop region (yet)'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Подрезка вида сегментирована. '
                'На данный момент мы не можем проверить сегментированные виды.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_reset_crop(self):
        # type: () -> str
        DEFAULT = 'You can reset view crop and run the check again'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Вы можете восстановить подрезку и запустить проверку снова'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementInsideSectionBox(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.Source3DView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if not self._view.is_section_box_active:
            self._result = self._result_section_box_is_off
            return

        if not self._view.section_box_contains_elem(self._elem):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_outside
            return

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is inside 3D view section box'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент в пределах границ 3D вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_section_box_is_off(self):
        # type: () -> str
        DEFAULT = 'Section box is turned off'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Границы 3D вида выключены'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_outside(self):
        # type: () -> str
        DEFAULT = 'Element is outside of the view section box'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится за пределами границ 3D вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if self._elem.is_annotation_category:
            return False

        if isinstance(self._view, sv.Source3DView):
            return True

        return False


class ElementInPlanViewRange(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceViewPlan) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        elem_bb = self._elem.get_bb(self._view)

        if isinstance(self._elem, ie.ViewTag):
            if not self._elem.get_parent_view().CropBoxActive:
                return

            elem_bb = self._elem.get_tagged_view_bb()

        if elem_bb is None:
            self._passed = None
            self._symbol = self._SYMBOL_WARNING
            self._result = self._result_failed_getting_elem_bb
            self._hint = self._hint_cant_check_without_bb
            return

        if self._view.is_elevation_below_view_depth(elem_bb.Max.Z):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_below_view_depth
            return

        if isinstance(self._elem, ie.ViewTag):
            if self._view.is_elevation_below_view_bottom(elem_bb.Max.Z):
                self._passed = False
                self._symbol = self._SYMBOL_CROSSMARK
                self._result = self._result_elem_is_below_view_bottom
                return

        if self._view.is_elevation_above_view_range(elem_bb.Min.Z):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_above_range
            return

        if self._view.is_elevation_above_cut_plane(elem_bb.Min.Z):
            self._passed = False
            self._symbol = self._SYMBOL_CROSSMARK
            self._result = self._result_elem_is_above_cut

            CATS_VIZ_ABOVE_CUT = (
                DB.BuiltInCategory.OST_GenericModel,
                DB.BuiltInCategory.OST_Windows,
                DB.BuiltInCategory.OST_Casework
            )
            vis_cat_ids = [DB.ElementId(cat) for cat in CATS_VIZ_ABOVE_CUT]
            category = self._elem.cat

            if category and category.Id in vis_cat_ids:
                self._set_default_good_result()

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is in plan view range'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент в пределах секущего диапазона'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_below_view_depth(self):
        # type: () -> str
        DEFAULT = 'Element is below the view depth'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится ниже глубины проецирования вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_below_view_bottom(self):
        # type: () -> str
        DEFAULT = 'Element is below the primary range bottom'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится ниже основного секущего диапазона'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_above_range(self):
        # type: () -> str
        DEFAULT = 'Element is above the view range'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится выше секущего диапазона'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_above_cut(self):
        # type: () -> str
        DEFAULT = 'Element is above the cut line'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится выше секущей плоскости'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if not isinstance(self._view, sv.SourceViewPlan):
            return False

        elem = self._elem

        if isinstance(elem, ie.ViewTag):

            if elem.is_elevation or elem.is_section:
                return True

        if not elem.is_model_category:
            return False

        return True


class ElementInSectionDepthRange(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceViewSection) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if self._elem.get_bb(self._view) is None:
            self._passed = False
            self._symbol = self._SYMBOL_WARNING
            self._result = self._result_failed_getting_elem_bb
            self._hint = self._hint_cant_check_without_bb
            return

        corners = self._elem.get_all_bb_corners(self._view)

        if not self._view.any_point_behind_view_pane(corners):
            self._symbol = self._SYMBOL_CROSSMARK
            self._passed = False
            self._result = self._result_elem_not_in_view_dir
            self._hint = self._hint_change_view_dir
            return

        if self._view.no_far_clip:
            return

        if self._view.all_points_behind_depth(corners):
            self._symbol = self._SYMBOL_CROSSMARK
            self._passed = False
            self._result = self._result_elem_is_behind_depth

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is in the range of the view section depth'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент в пределах глубины секущей плоскости'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_not_in_view_dir(self):
        # type: () -> str
        DEFAULT = 'Element is on the other side of the view direction'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится по другую сторону от направления вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_change_view_dir(self):
        # type: () -> str
        DEFAULT = (
            'You may want to flip the view '
            'or move it so it is looking at the element'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': 'Разверните или подвиньте вид, чтобы он смотрел на элемент'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_is_behind_depth(self):
        # type: () -> str
        DEFAULT = 'Element is further than the section depth.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент находится за пределами глубины подрезки вида'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if self._elem.is_annotation_category:
            return False

        if isinstance(self._view, sv.SourceViewSection):
            return True

        return False


class ElementInSectionDepthCueing(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceViewSection) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if not self._view.is_depth_cueing_enabled:
            return

        corners = self._elem.get_all_bb_corners(self._view)

        if self._view.all_points_behind_depth_cue_end(corners):
            self._symbol = self._SYMBOL_CROSSMARK
            self._passed = False
            self._result = self._result_fade_end_too_close

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is in section depth cueing range'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент в пределах глубины затемнения'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def description(self):
        # type: () -> str
        DEFAULT = '"Graphics Display Options" -> "Depth Cueing"'

        locales = {
            'en_us': DEFAULT,
            'ru': '"Параметры отображения графики" -> "Затемнение"'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_fade_end_too_close(self):
        # type: () -> str
        DEFAULT = 'Depth cueing fade end is too close'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Конечная точка затемнения подвинута слишком близко'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        if self._elem.is_annotation_category:
            return False

        if isinstance(self._view, sv.SourceViewSection):
            return True

        return False


class ElementNotInDesignOption(Check):
    def __init__(self, elem):
        # type: (ie.InvisibleElement) -> None
        self._elem = elem
        self._set_default_good_result()

    def check(self):
        design_option = self._elem.design_option

        if design_option is None:
            return

        self._symbol = self._SYMBOL_WARNING
        self._passed = False

        is_primary = ''
        if design_option.IsPrimary:
            is_primary = self._primary_option_txt

        self._result = self._result_elem_in_opt.format(
            design_option.Name,
            is_primary
        )

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is not in design option.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент не находится в вариантах конструкций'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _primary_option_txt(self):
        # type: () -> str
        DEFAULT = ' (primary option)'

        locales = {
            'en_us': DEFAULT,
            'ru': ' (основной вариант)'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_elem_in_opt(self):
        # type: () -> str
        DEFAULT = (
            'Element is in design option "{}{}". '
            'Currently there is no method to check '
            'if this option is visible in view. '
            'You will have to do it manually.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Элемент в вариантах конструкций "{}{}". '
                'На данный момент мы не можем проверить, '
                'скрыт ли этот вариант конструкций на виде. '
                'Вам придётся это сделать вручную.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ElementNotHiddenByViewFilter(Check):
    def __init__(self, elem, view):
        # type: (ie.InvisibleElement, sv.SourceViewSection) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        for filter in self._view.get_filters():
            if self._view.is_elem_hidden_by_filter(self._elem, filter):
                self._symbol = self._SYMBOL_CROSSMARK
                self._passed = False
                self._result = self._result_hidden_by_filter.format(
                    filter.Name
                )
                return

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Element is not hidden by view filter.'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент не скрыт фильтром'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_hidden_by_filter(self):
        # type: () -> str
        DEFAULT = 'Element is hidden by filter "{}"'

        locales = {
            'en_us': DEFAULT,
            'ru': 'Элемент скрыт фильтром "{}"'
        }

        return applocales.get_locale_string(locales) or DEFAULT


class ViewScaleNotCoarserViewTag(Check):
    def __init__(self, elem, view):
        # type: (ie.ViewTag, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if self._elem.coarser_scale_is_custom:
            self._symbol = self._SYMBOL_WARNING
            self._passed = False
            self._result = self._result_hide_coarser_is_custom.format(
                DB.LabelUtils.GetLabelFor(
                    DB.BuiltInParameter.SECTION_COARSER_SCALE_PULLDOWN_METRIC
                )
            )
            return

        if not self._elem.is_visible_at_scale(self._view.scale):
            self._symbol = self._SYMBOL_CROSSMARK
            self._passed = False
            self._result = self._result_scale_is_coarser

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'Source view scale is not coarser than view tag settings.'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Масштаб исходного вида не крупнее, чем настройки марки вида.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_hide_coarser_is_custom(self):
        DEFAULT = 'View tag parameter "{}" is set to custom.'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Параметр марки вида "{}" задан как "Пользовательский".'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _hint_coarser_is_custom(self):
        DEFAULT = 'Can not perform check for this setting.'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Для такой настройки нет возможности сделать проверку.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_scale_is_coarser(self):
        DEFAULT = 'View scale is coarser'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Масштаб исходного вида крупнее'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        # type: () -> bool
        if isinstance(self._elem, ie.ViewTag):

            if self._elem.shown_in_parent_view_only:
                return False

            return True

        return False


class ViewTagShownInThisOrIntersectingViews(Check):
    def __init__(self, elem, view):
        # type: (ie.ViewTag, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        if self._elem.shown_in_parent_view_only:
            parent_view = self._elem.get_parent_view()

            if parent_view is None:
                self._SYMBOL_WARNING
                self._passed = False
                self._result = self._result_failed_define_parent
                return

            if parent_view.Id != self._view.id:
                self._symbol = self._SYMBOL_CROSSMARK
                self._passed = False
                parent_name = str(parent_view.Name)
                self._result = self._result_in_parent_only.format(parent_name)

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'View tag is shown on this or intersecting views.'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Марка вида отображается на этом или пересекающихся видах.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_failed_define_parent(self):
        DEFAULT = (
            'View tag is shown in parent view only '
            'but we failed to define it.'
        )

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Марка вида отображается только в родительском виде,'
                'но его не удалось определить.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_in_parent_only(self):
        DEFAULT = 'View tag is shown in parent view only. Parent view name: {}'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Марка вида отображается только в родительском виде. '
                'Имя родительского вида: {}'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        # type: () -> bool
        if isinstance(self._elem, ie.ViewTag):
            return True

        return False


class ViewTagDisciplineMatchesView(Check):
    def __init__(self, elem, view):
        # type: (ie.ViewTag, sv.SourceView) -> None
        self._elem = elem
        self._view = view
        self._set_default_good_result()

    def check(self):
        COORDINATION = DB.ViewDiscipline.Coordination

        view_discipline = self._view.get_discipline()
        view_tag_discipline = self._elem.get_discipline()

        if COORDINATION not in (view_discipline, view_tag_discipline):
            if view_discipline != view_tag_discipline:
                self._passed = False
                self._symbol = self._SYMBOL_CROSSMARK
                self._result = self._result_mismatches.format(
                    self._elem.get_discipline_txt(),
                    self._view.get_discipline_txt()
                )

    @property
    def title(self):
        # type: () -> str
        DEFAULT = 'View tag discipline matches view discipline'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Дисциплина марки вида соответствует дисциплине вида'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _result_mismatches(self):
        # type: () -> str
        DEFAULT = 'View tag discipline is {}, but view discipline is {}.'

        locales = {
            'en_us': DEFAULT,
            'ru': (
                'Дисциплина марки вида {}, но дисциплина вида {}.'
            )
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def worth_checking(self):
        # type: () -> bool
        if not isinstance(self._elem, ie.ViewTag):
            return False

        if not self._elem.has_discipline:
            return False

        if not self._view.has_discipline:
            return False

        return True
