from dataclasses import dataclass
from .rows import identity, normalize_payload, payload_fingerprint, payload_data


@dataclass(frozen=True)
class ObservationRevision:
    row_id: object
    revision: int
    payload: object


@dataclass(frozen=True)
class RevisionDecision:
    revision: ObservationRevision
    insert: bool


def normalize_revision(value):
    if isinstance(value, ObservationRevision):
        value = dict(row_id=value.row_id, revision=value.revision, payload=value.payload)
    if not isinstance(value, dict) or set(value) != {"row_id", "revision", "payload"}:
        raise ValueError("invalid revision")
    row_id = identity(value["row_id"])
    rev = value["revision"]
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 1:
        raise ValueError("revision must be a positive integer")
    return ObservationRevision(row_id, rev, normalize_payload(value["payload"]))


def revision_data(revision):
    return dict(row_id=revision.row_id, revision=revision.revision,
                payload=payload_data(revision.payload))


def plan_revision_changes(revisions, store):
    decisions = []
    seen = set()
    for rev in revisions:
        if rev.row_id in seen:
            raise ValueError("duplicate row in batch")
        seen.add(rev.row_id)
        old = store.load_history(rev.row_id, rev.revision)
        if old is not None:
            if payload_fingerprint(old.payload) != payload_fingerprint(rev.payload):
                raise ValueError("same revision has different content")
            decisions.append(RevisionDecision(rev, False))
            continue
        current = store.load_current(rev.row_id)
        if current is not None and rev.revision <= current.revision:
            raise ValueError("unaccepted stale revision")
        decisions.append(RevisionDecision(rev, True))
    return decisions
