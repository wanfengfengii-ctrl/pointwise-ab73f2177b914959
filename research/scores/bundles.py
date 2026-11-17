from dataclasses import dataclass
from fractions import Fraction
from .design import build_design
from .projection import residualize_design
from .groups import aggregate_group_scores, GroupAffineScore


@dataclass(frozen=True)
class ScoreBundle:
    cohort_id: int
    roles: object
    row_revisions: tuple
    row_groups: tuple
    dimension: int
    nuisance_rank: int
    tool_rank: int
    scores: tuple

    def audit(self):
        return dict(cohort_id=self.cohort_id,
                    roles=dict(y=self.roles.y, x=self.roles.x,
                               z=list(self.roles.z), w=list(self.roles.w)),
                    row_revisions=[list(r) for r in self.row_revisions],
                    row_groups=list(self.row_groups), dimension=self.dimension,
                    nuisance_rank=self.nuisance_rank, tool_rank=self.tool_rank,
                    groups=[dict(group=s.group, a=list(s.a), d=list(s.d)) for s in self.scores])


def validate_score_bundle(bundle):
    if bundle.dimension != len(bundle.roles.z) or not 0 <= bundle.dimension <= 2:
        raise ValueError("invalid joint coordinate dimension")
    if len(bundle.row_groups) != len(bundle.row_revisions):
        raise ValueError("group provenance mismatch")
    if len({s.group for s in bundle.scores}) != len(bundle.scores):
        raise ValueError("duplicate group score")
    if set(bundle.row_groups) != {s.group for s in bundle.scores}:
        raise ValueError("group identity mismatch")
    if any(len(s.a) != bundle.dimension or len(s.d) != bundle.dimension for s in bundle.scores):
        raise ValueError("incomplete affine vector")
    if not 0 <= bundle.tool_rank <= bundle.dimension:
        raise ValueError("invalid effective tool rank")


def build_score_bundle(cohort):
    design = build_design(cohort)
    residual = residualize_design(design)
    scores = aggregate_group_scores(residual)
    dimension = len(design.z)
    if dimension > 1:
        # Carry a pooled instrument index in the original coordinate envelope.
        def pooled(values):
            return (sum(values, Fraction(0)) / dimension,) + (Fraction(0),) * (dimension - 1)
        scores = tuple(GroupAffineScore(s.group, pooled(s.a), pooled(s.d)) for s in scores)
    bundle = ScoreBundle(design.cohort_id, design.roles, design.row_revisions, design.groups,
                         dimension, residual.nuisance_rank, residual.tool_rank, scores)
    validate_score_bundle(bundle)
    return bundle
