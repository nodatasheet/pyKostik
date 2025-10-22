import csv
from collections import OrderedDict

try:
    from typing import Iterable, Self
except ImportError:
    pass


class TableError(Exception):
    pass


class RowHeadersQtyError(TableError):
    pass


class RowHeadersMismatchError(TableError):
    pass


class TypeValidationError(TableError):
    pass


class OrderedDictReader:
    """
    Similar to csv.DictReader, but returns OrderedDict for rows.
    Also has property indicating if fields qty differs from headers
    (only checked at iteration).
    """

    def __init__(self, f, fieldnames=None, restkey=None, restval=None,
                 dialect="excel", *args, **kwds):
        if fieldnames is not None and iter(fieldnames) is fieldnames:
            fieldnames = list(fieldnames)
        self._fieldnames = fieldnames   # list of keys for the dict
        self.restkey = restkey          # key to catch long rows
        self.restval = restval          # default value for short rows
        self.reader = csv.reader(f, dialect, *args, **kwds)
        self.dialect = dialect
        self.line_num = 0

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    @property
    def fieldnames(self):
        if self._fieldnames is None:
            try:
                self._fieldnames = next(self.reader)
            except StopIteration:
                pass
        self.line_num = self.reader.line_num
        return self._fieldnames

    @fieldnames.setter
    def fieldnames(self, value):
        self._fieldnames = value

    def next(self):
        if self.line_num == 0:
            # Used only for its side effect.
            self.fieldnames
        row = next(self.reader)
        self.line_num = self.reader.line_num

        # unlike the basic reader, we prefer not to return blanks,
        # because we will typically wind up with a dict full of None
        # values
        while row == []:
            row = next(self.reader)
        d = OrderedDict(zip(self.fieldnames, row))
        lf = len(self.fieldnames)
        lr = len(row)
        self.is_fields_qty_correct = True
        if lf < lr:
            self.is_fields_qty_correct = False
            d[self.restkey] = row[lf:]
        elif lf > lr:
            self.is_fields_qty_correct = False
            for key in self.fieldnames[lr:]:
                d[key] = self.restval
        return d


class Table(object):
    def __init__(self):
        # type: () -> None
        self._headers = []
        self._rows = []  # type: list[OrderedDict]

    @classmethod
    def from_csv(cls, file_path):
        # type: (str) -> Self
        new_table = cls()
        reader = cls._read_csv(file_path)
        for row in reader:
            new_table.add_row(row)
        return new_table

    @classmethod
    def from_matrix(cls, matrix):
        # type: (list[list]) -> Self
        new_table = cls()
        headers, rows = matrix[0], matrix[1:]
        new_table._headers = headers
        for i, row in enumerate(rows, 1):
            if len(row) != len(headers):
                raise RowHeadersQtyError(
                    'Row {} fields qty differs from headers'
                    .format(i)
                )
            d = OrderedDict(zip(headers, row))
            new_table.add_row(d)
        return new_table

    @classmethod
    def _read_csv(cls, file_path, **kwargs):
        # type: (str, any) -> Iterable[OrderedDictReader]
        with open(file_path, 'r') as csvfile:
            dict_reader = OrderedDictReader(csvfile, **kwargs)
            for row in dict_reader:
                cls._validate_correct_fields_qty(dict_reader)
                yield row

    @classmethod
    def _validate_correct_fields_qty(cls, dict_reader):
        # type: (OrderedDictReader) -> None
        if not dict_reader.is_fields_qty_correct:
            raise RowHeadersQtyError(
                'Row {} fields qty differs from headers'
                .format(dict_reader.reader.line_num - 1)
            )

    @property
    def headers(self):
        return list(self._headers)

    @property
    def rows(self):
        return self._rows

    @property
    def is_empty(self):
        return len(self._rows) == 0

    def lookup(self,
               lookup_attr,
               conditions,
               try_numeric_compare=False,
               round_digits=9,
               default=None):
        # type: (str, dict, bool, int, any) -> str

        if not self._are_conditions_in_headers(conditions):
            return default

        if try_numeric_compare:
            conditions = self._numerify(conditions, round_digits)

        for row in self._rows:
            if self._match_found(conditions,
                                 try_numeric_compare,
                                 round_digits,
                                 row):

                return row.get(lookup_attr, default)

        return default

    def _match_found(self, conditions, try_numeric_compare, round_digits, row):
        # type: (dict, bool, int, OrderedDict) -> bool
        if try_numeric_compare:
            row = self._numerify(row, round_digits)

        if all(row[k] == v for k, v in conditions.items()):
            return True

    def _numerify(self, dictionary, round_digits):
        # type: (dict, int) -> dict
        return {
            k: self._try_float(v, round_digits) for k, v in dictionary.items()
        }

    def _try_float(self, value, round_digits):
        # type: (str, int) -> float | str
        if value is None:
            return value
        try:
            return round(float(value), round_digits)
        except Exception:
            return value

    def _are_conditions_in_headers(self, conditions):
        # type: (dict) -> bool
        return all(k in self.headers for k in conditions)

    def add_row(self, row):
        # type: (OrderedDict) -> None
        self._validate_type(row, OrderedDict)

        if not self._headers:
            self._headers = row.keys()

        self._validate_headers(row)
        self._rows.append(row)

    def _validate_headers(self, row):
        # type: (OrderedDict) -> None
        if not self.headers:
            return

        if len(row) != len(self._headers):
            raise RowHeadersQtyError(
                'Row fields qty differs from headers'
            )

        for k, h in zip(row, self.headers):
            if k != h:
                raise RowHeadersMismatchError(
                    'Row fields do not match existing headers'
                )

    def _validate_type(self, provided, expected):
        # type: (object, type) -> None
        if not isinstance(provided, expected):
            raise TypeValidationError(
                'expected {}, provided {}'
                .format(expected.__name__, type(provided).__name__)
            )

    def to_matrix(self):
        # type: () -> list[list]
        matrix = [self.headers]
        for r in self.rows:
            matrix.append(r.values())
        return matrix

    def write_to_csv(self, file_path, **kwargs):
        # type: (str, any) -> None
        if kwargs.get('lineterminator') is None:
            kwargs['lineterminator'] = '\n'

        with open(file_path, 'w') as csv_file:
            writer = csv.writer(csv_file, **kwargs)
            writer.writerows(self.to_matrix())
