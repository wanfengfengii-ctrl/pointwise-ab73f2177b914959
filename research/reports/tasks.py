from dataclasses import dataclass
from research.cohorts.specs import spec_data
from research.inference.statistic import TestSpecification


@dataclass(frozen=True)
class TaskBinding:
    cohort_id: int
    specification: object
    roles: dict

    def as_dict(self):
        return dict(cohort_id=self.cohort_id, threshold=self.specification.threshold,
                    version=self.specification.version, roles=self.roles)


def validate_execution_state(state):
    if state not in ("pending", "success"):
        raise RuntimeError("invalid task state")
    return state == "pending"


class TaskService:
    def __init__(self, cohort_reader, store):
        self.cohort_reader, self.store = cohort_reader, store

    def create_task(self, cohort_id, c):
        specification = TestSpecification(c)
        with self.store.connection:
            cohort = self.cohort_reader.read_cohort(cohort_id)
            roles = spec_data(cohort.spec)
            roles.pop("row_ids")
            binding = TaskBinding(cohort_id, specification, roles)
            task_id = self.store.insert_task(binding.as_dict())
        return task_id

    def load_binding(self, task_id):
        binding, state = self.store.load_task(task_id)
        validate_execution_state(state)
        TestSpecification(binding["threshold"], binding["version"])
        return binding, state
