from pyrevit.revit.db import transaction as prt
from pyrevit.revit.db import failure as prf
from pyrevit import DOCS, DB

from pykostik.revit.db import failure as pkf


class Transaction(prt.Transaction):
    """Same as `pyrevit.revit.Transaction`
    but can swallow specific errors.
    """

    def __init__(self, name=None,
                 doc=None,
                 clear_after_rollback=False,
                 show_error_dialog=False,
                 swallow_errors=[],
                 log_errors=True,
                 nested=False):
        doc = doc or DOCS.doc
        # create nested transaction if one is already open
        if doc.IsModifiable or nested:
            self._rvtxn = \
                DB.SubTransaction(doc)
        else:
            self._rvtxn = \
                DB.Transaction(
                    doc, name if name else prt.DEFAULT_TRANSACTION_NAME)
            self._fhndlr_ops = self._rvtxn.GetFailureHandlingOptions()
            self._fhndlr_ops = \
                self._fhndlr_ops.SetClearAfterRollback(clear_after_rollback)
            self._fhndlr_ops = \
                self._fhndlr_ops.SetForcedModalHandling(show_error_dialog)
            if swallow_errors:
                if hasattr(swallow_errors, '__iter__'):
                    self._fhndlr_ops = \
                        self._fhndlr_ops.SetFailuresPreprocessor(
                            pkf.SpecificFailureSwallower(
                                specific_failures=swallow_errors)
                        )
                else:
                    self._fhndlr_ops = \
                        self._fhndlr_ops.SetFailuresPreprocessor(
                            prf.FailureSwallower()
                        )
            self._rvtxn.SetFailureHandlingOptions(self._fhndlr_ops)
        self._logerror = log_errors
