from dataclasses import dataclass
from research.records.rows import identity, identity_key


@dataclass(frozen=True)
class ColumnRoles:
    y: str
    x: str
    z: tuple = ()
    w: tuple = ()

    @property
    def columns(self):
        return (self.y, self.x) + self.z + self.w


@dataclass(frozen=True)
class CohortSpec:
    row_ids: tuple
    roles: ColumnRoles


def normalize_spec(spec):
    if isinstance(spec, CohortSpec):
        rows, roles = spec.row_ids, spec.roles
    elif isinstance(spec, dict) and set(spec) == {"row_ids", "y", "x", "z", "w"}:
        rows = spec["row_ids"]
        if not isinstance(spec["z"], (list, tuple)) or not isinstance(spec["w"], (list, tuple)):
            raise ValueError("tool and nuisance roles must be sequences")
        roles = ColumnRoles(spec["y"], spec["x"], tuple(spec["z"]), tuple(spec["w"]))
    else:
        raise ValueError("invalid cohort specification")
    if not isinstance(rows, (list, tuple)) or not isinstance(roles, ColumnRoles):
        raise ValueError("invalid cohort specification")
    rows = tuple(identity(r) for r in rows)
    if len(set(rows)) != len(rows):
        raise ValueError("duplicate candidate")
    roles = ColumnRoles(roles.y, roles.x, tuple(roles.z), tuple(roles.w))
    return CohortSpec(tuple(sorted(rows, key=identity_key)), roles)


def validate_spec(spec, known_columns):
    if len(spec.row_ids) > 24 or len(spec.roles.z) > 2 or len(spec.roles.w) > 4:
        raise ValueError("cohort exceeds public dimensions")
    columns = spec.roles.columns
    if any(not isinstance(c, str) or not c for c in columns):
        raise ValueError("invalid role name")
    if len(set(columns)) != len(columns):
        raise ValueError("duplicate column role")
    if set(columns) - set(known_columns):
        raise ValueError("unknown column")


def spec_data(spec):
    return dict(row_ids=list(spec.row_ids), y=spec.roles.y, x=spec.roles.x,
                z=list(spec.roles.z), w=list(spec.roles.w))
