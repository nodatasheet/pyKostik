from pyrevit.revit.db import failure as prf
from pyrevit import DB
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger

mlogger = get_logger(__name__)


class SpecificFailureSwallower(prf.FailureSwallower):
    """Same as `pyrevit.revit.db.failure.FailureSwallower`
    but swallows only supplied failures.
    """

    def __init__(self, log_errors=True, specific_failures=[]):
        """Same as `pyrevit.revit.db.failure.FailureSwallower`
        but swallows only supplied failures.
        """
        # type: (bool, list[DB.FailureDefinitionId]) -> None
        self._logerror = log_errors
        self._failures_swallowed = []
        self._specific_failures = specific_failures

    def preprocess_specific_failures(self, failure_accessor):
        # type: (DB.FailuresAccessor) -> DB.FailureProcessingResult
        """Pythonic wrapper for `PreprocessFailures` interface method.
        """
        return self.PreprocessFailures(failure_accessor)

    def PreprocessFailures(self, failuresAccessor):
        """Required IFailuresPreprocessor interface method"""
        severity = failuresAccessor.GetSeverity()
        # log some info
        mlogger.debug('processing failure with severity: %s', severity)

        if severity == coreutils.get_enum_none(DB.FailureSeverity):
            mlogger.debug('clean document. returning with'
                          'FailureProcessingResult.Continue')
            return DB.FailureProcessingResult.Continue

        # log the failure messages
        failures = failuresAccessor.GetFailureMessages()
        mlogger.debug('collected %s failure messages.', len(failures))

        # go through failures and attempt resolution
        action_taken = False
        for failure in failures:

            failure_id = failure.GetFailureDefinitionId()

            if failure_id in self._specific_failures:
                failure_guid = getattr(failure_id, 'Guid', '')
                failure_severity = failure.GetSeverity()
                failure_desc = failure.GetDescriptionText()
                failure_has_res = failure.HasResolutions()

                # log failure info
                mlogger.debug('processing failure msg: %s', failure_guid)
                mlogger.debug('\tseverity: %s', failure_severity)
                mlogger.debug('\tdescription: %s', failure_desc)
                mlogger.debug('\telements: %s',
                              [x.IntegerValue for x in failure.GetFailingElementIds()])
                mlogger.debug('\thas resolutions: %s', failure_has_res)

                # attempt resolution
                mlogger.debug('attempt resolving failure: %s', failure_guid)

                # if it's a warning and does not have any resolution
                # delete it! it might have a popup window
                if not failure_has_res \
                        and failure_severity == DB.FailureSeverity.Warning:
                    failuresAccessor.DeleteWarning(failure)
                    mlogger.debug(
                        'deleted warning with no acceptable resolution: %s',
                        failure_guid
                    )
                    continue

                # find failure definition id
                # at this point the failure_has_res is True
                failure_def_accessor = prf.get_failure_by_id(failure_id)
                default_res = failure_def_accessor.GetDefaultResolutionType()

                # iterate through resolution options, pick one and resolve
                for res_type in prf.RESOLUTION_TYPES:
                    if default_res == res_type:
                        mlogger.debug(
                            'using default failure resolution: %s', res_type)
                        self._set_and_resolve(
                            failuresAccessor, failure, res_type)
                        action_taken = True
                        break
                    elif failure.HasResolutionOfType(res_type):
                        mlogger.debug(
                            'setting failure resolution to: %s', res_type)
                        self._set_and_resolve(
                            failuresAccessor, failure, res_type)
                        # marked as action taken
                        action_taken = True
                        break
                    else:
                        mlogger.debug(
                            'invalid failure resolution: %s', res_type)

            # report back
            if action_taken:
                mlogger.debug('resolving failures with '
                              'FailureProcessingResult.ProceedWithCommit')
                return DB.FailureProcessingResult.ProceedWithCommit
            else:
                mlogger.debug('resolving failures with '
                              'FailureProcessingResult.Continue')
                return DB.FailureProcessingResult.Continue
