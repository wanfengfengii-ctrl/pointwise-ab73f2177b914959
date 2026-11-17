from research.scores.bundles import build_score_bundle
from research.inference.rank_cells import infer_acceptance_cells
from .sets import normalize_confidence_set
from .readback import ReportReader


class ReportExecutor:
    def __init__(self, tasks, cohort_reader, store):
        self.tasks, self.cohort_reader, self.store = tasks, cohort_reader, store

    def execute(self, task_id, *, fault=None):
        binding, state = self.tasks.load_binding(task_id)
        reader = ReportReader(self.store)
        if state == "success":
            return reader.read_report(task_id)
        cohort = self.cohort_reader.read_cohort(binding["cohort_id"])
        bundle = build_score_bundle(cohort)
        if bundle.audit()["roles"] != binding["roles"]:
            raise ValueError("task and score coordinates differ")
        if fault is not None:
            fault("after_scores")
        cells = infer_acceptance_cells(bundle, binding["threshold"])
        confidence_set = normalize_confidence_set(cells)
        with self.store.connection:
            self.store.connection.execute("BEGIN")
            current_binding, current_state = self.tasks.load_binding(task_id)
            if current_binding != binding:
                raise ValueError("task binding changed")
            if current_state == "pending":
                callback = None if fault is None else lambda: fault("before_commit")
                self.store.publish_complete(task_id, binding, confidence_set, bundle.audit(), callback)
        return reader.read_report(task_id)
