from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentSnapshot:
    rows: dict
    columns: frozenset


class CurrentRows:
    def __init__(self, store):
        self.store = store

    def snapshot(self):
        rows = {r.row_id: r for r in self.store.current_all()}
        return CurrentSnapshot(rows, frozenset(self.known_columns()))

    def known_columns(self):
        columns = set()
        for (body,) in self.store.connection.execute("SELECT body FROM observation_history"):
            from .rows import loads
            columns.update(loads(body)["payload"]["values"])
        return columns
