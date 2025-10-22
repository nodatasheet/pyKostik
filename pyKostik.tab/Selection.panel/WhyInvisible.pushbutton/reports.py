# encoding: utf-8

import sys
import traceback
from pyrevit import script
from pyrevit.coreutils import applocales

import checks as ch
import invisible_element as ie


output = script.get_output()


class Report(object):
    def __init__(self, elem):
        # type: (ie.InvisibleElement) -> None
        self._elem = elem
        self._checks = []  # type: list[ch.Check]

    def add(self, check):
        # type: (ch.Check) -> None
        self._checks.append(check)

    def run_checks(self):
        for check in self._checks:
            try:
                check.check()
            except Exception as err:
                traceback = self._format_traceback()
                check.set_check_error(str(err), traceback)

    def print_results(self):
        link = output.linkify(self._elem.id)
        output.print_md(self._main_title.format(link))
        for check in self._checks:
            self.print_result(check)

    def print_result(self, check):
        # type: (ch.Check) -> None
        output.print_md(
            self._check_title.format(check.symbol, check.title)
        )

        if check.description:
            output.print_md(
                self._check_description_title.format(check.description)
            )

        output.print_md(self._check_result_title.format(check.result))

        if check.hint:
            output.print_md(self._check_hint_title.format(check.hint))

        if check.failed_with_error:
            print(check.error_trace)

    def _format_traceback(self):
        etype, value, tb = sys.exc_info()
        stack_trace = ['Traceback (most recent call last):\n']

        for filename, lineno, name, line in traceback.extract_tb(tb):
            item = 'File "{}", line {}, in {}\n'.format(filename, lineno, name)
            stack_trace.append(item)

        stack_trace += traceback.format_exception_only(etype, value)
        err_code = ''.join(stack_trace)

        return err_code

    @property
    def _main_title(self):
        # type: () -> str
        DEFAULT = '# Why element {} might be invisible:'

        locales = {
            'en_us': DEFAULT,
            'ru': '# Почему элемент {} может быть невидимым:'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _check_title(self):
        # type: () -> str
        DEFAULT = '## {} {}'

        locales = {
            'en_us': DEFAULT,
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _check_description_title(self):
        # type: () -> str
        DEFAULT = '  >*Description: {}*'

        locales = {
            'en_us': DEFAULT,
            'ru': '  >*Описание: {}*'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _check_result_title(self):
        # type: () -> str
        DEFAULT = '  >**Result: {}**'

        locales = {
            'en_us': DEFAULT,
            'ru': '  >**Результат: {}**'
        }

        return applocales.get_locale_string(locales) or DEFAULT

    @property
    def _check_hint_title(self):
        # type: () -> str
        DEFAULT = '  >Hint: {}'

        locales = {
            'en_us': DEFAULT,
            'ru': '  >Совет: {}'
        }

        return applocales.get_locale_string(locales) or DEFAULT
