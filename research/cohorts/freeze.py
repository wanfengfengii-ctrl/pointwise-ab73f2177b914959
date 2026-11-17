from dataclasses import dataclass
from .specs import normalize_spec, validate_spec, spec_data
from .selection import select_complete_rows


@dataclass(frozen=True)
class FreezeReceipt:
    cohort_id: int
    adopted: list
    excluded: list

    def as_dict(self):
        return dict(cohort_id=self.cohort_id, adopted=self.adopted, excluded=self.excluded)


class CohortFreezer:
    def __init__(self, current, store):
        self.current, self.store = current, store

    def freeze(self, spec):
        spec = normalize_spec(spec)
        with self.store.connection:
            self.store.connection.execute("BEGIN")
            snapshot = self.current.snapshot()
            validate_spec(spec, snapshot.columns)
            selected = select_complete_rows(spec, snapshot)
            body = dict(spec=spec_data(spec), adopted=selected.adopted, excluded=selected.excluded)
            cohort_id = self.store.insert_frozen(body)
        adopted = [dict(row_id=r["row_id"], revision=r["revision"],
                        group=r["payload"]["group"]) for r in selected.adopted]
        return FreezeReceipt(cohort_id, adopted, selected.excluded).as_dict()
