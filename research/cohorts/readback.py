from dataclasses import dataclass
from copy import deepcopy
from .specs import normalize_spec


@dataclass(frozen=True)
class FrozenCohort:
    cohort_id: int
    spec: object
    rows: tuple
    excluded: tuple


class CohortReader:
    def __init__(self, store):
        self.store = store

    def read_cohort(self, cohort_id):
        body = deepcopy(self.store.load_frozen(cohort_id))
        return FrozenCohort(cohort_id, normalize_spec(body["spec"]),
                            tuple(body["adopted"]), tuple(body["excluded"]))
