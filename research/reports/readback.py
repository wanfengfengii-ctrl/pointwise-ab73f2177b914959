from dataclasses import dataclass
from copy import deepcopy


@dataclass
class AnalysisReport:
    task_id: int
    binding: dict
    confidence_set: object
    audit: dict
    receipt: dict


class ReportReader:
    def __init__(self, store):
        self.store = store

    def read_report(self, task_id):
        body = deepcopy(self.store.load_published(task_id))
        return AnalysisReport(body["task_id"], body["binding"], body["confidence_set"],
                              body["audit"], body["receipt"])
