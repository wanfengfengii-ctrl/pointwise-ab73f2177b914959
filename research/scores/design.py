from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class AnalysisDesign:
    cohort_id: int
    roles: object
    row_revisions: tuple
    groups: tuple
    y: tuple
    x: tuple
    z: tuple
    w: tuple


def validate_design_binding(design):
    n = len(design.y)
    if not (len(design.x) == len(design.groups) == len(design.row_revisions) == n):
        raise ValueError("unaligned frozen design")
    if len(design.z) != len(design.roles.z) or len(design.w) != len(design.roles.w):
        raise ValueError("coordinate dimension mismatch")
    if any(len(v) != n for v in design.z + design.w):
        raise ValueError("unaligned design columns")
    if len(set(design.row_revisions)) != n:
        raise ValueError("duplicate frozen identity")


def build_design(cohort):
    roles = cohort.spec.roles
    def column(name):
        return tuple(Fraction(r["payload"]["values"][name]) for r in cohort.rows)
    result = AnalysisDesign(
        cohort.cohort_id, roles,
        tuple((r["row_id"], r["revision"]) for r in cohort.rows),
        tuple(r["payload"]["group"] for r in cohort.rows),
        column(roles.y), column(roles.x),
        tuple(column(c) for c in roles.z), tuple(column(c) for c in roles.w))
    validate_design_binding(result)
    return result
