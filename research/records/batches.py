from dataclasses import dataclass
from .rows import identity, identity_key, dumps
from .revisions import normalize_revision, revision_data, plan_revision_changes


@dataclass(frozen=True)
class BatchReceipt:
    batch_id: object
    inserted: tuple
    replayed: tuple

    def as_dict(self):
        return dict(batch_id=self.batch_id, inserted=list(self.inserted),
                    replayed=list(self.replayed))


class BatchService:
    def __init__(self, store):
        self.store = store

    def apply(self, batch_id, revisions):
        identity(batch_id)
        revisions = [normalize_revision(r) for r in revisions]
        revisions.sort(key=lambda r: identity_key(r.row_id))
        if len({r.row_id for r in revisions}) != len(revisions):
            raise ValueError("duplicate row in batch")
        request = dumps([revision_data(r) for r in revisions])
        with self.store.connection:
            old = self.store.load_receipt(batch_id)
            if old is not None:
                if old[0] != request:
                    raise ValueError("batch identity conflict")
                return old[1]
            decisions = plan_revision_changes(revisions, self.store)
            receipt = BatchReceipt(
                batch_id,
                tuple([d.revision.row_id, d.revision.revision] for d in decisions if d.insert),
                tuple([d.revision.row_id, d.revision.revision] for d in decisions if not d.insert))
            result = receipt.as_dict()
            self.store.write_batch(batch_id, request, decisions, result)
        return result
