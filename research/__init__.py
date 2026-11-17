import sqlite3
from .records.store import RecordStore
from .records.batches import BatchService
from .records.current import CurrentRows
from .cohorts.store import CohortStore
from .cohorts.freeze import CohortFreezer
from .cohorts.readback import CohortReader
from .reports.store import ReportStore
from .reports.tasks import TaskService
from .reports.publish import ReportExecutor
from .reports.readback import ReportReader


class Archive:
    def __init__(self, path=":memory:"):
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.records = RecordStore(self.connection)
        self.cohorts = CohortStore(self.connection)
        self.reports = ReportStore(self.connection)
        self.records.initialize()
        self.cohorts.initialize()
        self.reports.initialize()
        self._batches = BatchService(self.records)
        self._freezer = CohortFreezer(CurrentRows(self.records), self.cohorts)
        self._cohort_reader = CohortReader(self.cohorts)
        self._tasks = TaskService(self._cohort_reader, self.reports)
        self._executor = ReportExecutor(self._tasks, self._cohort_reader, self.reports)
        self._reader = ReportReader(self.reports)

    def apply(self, batch_id, revisions):
        return self._batches.apply(batch_id, revisions)

    def freeze(self, spec):
        return self._freezer.freeze(spec)

    def read_cohort(self, cohort_id):
        return self._cohort_reader.read_cohort(cohort_id)

    def create_task(self, cohort_id, c):
        return self._tasks.create_task(cohort_id, c)

    def execute(self, task_id, *, fault=None):
        return self._executor.execute(task_id, fault=fault)

    def read_report(self, task_id):
        return self._reader.read_report(task_id)

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.close()
