from dataclasses import dataclass
from research.records.rows import payload_data


@dataclass(frozen=True)
class SelectionResult:
    adopted: list
    excluded: list


def exclusion_reason(revision, columns):
    if revision is None:
        return "not_found"
    if revision.payload.withdrawn:
        return "withdrawn"
    if revision.payload.group is None:
        return "missing_group"
    missing = [c for c in columns if revision.payload.values.get(c) is None]
    return "missing:" + ",".join(missing) if missing else None


def select_complete_rows(spec, snapshot):
    adopted, excluded = [], []
    for row_id in spec.row_ids:
        rev = snapshot.rows.get(row_id)
        reason = exclusion_reason(rev, spec.roles.columns)
        if reason is not None:
            excluded.append(dict(row_id=row_id, revision=None if rev is None else rev.revision,
                                 reason=reason))
        else:
            adopted.append(dict(row_id=row_id, revision=rev.revision,
                                payload=payload_data(rev.payload)))
    if len({r["payload"]["group"] for r in adopted}) > 8:
        raise ValueError("more than eight adopted groups")
    return SelectionResult(adopted, excluded)
