from dataclasses import dataclass
from fractions import Fraction
from research.records.rows import identity_key


@dataclass(frozen=True)
class GroupAffineScore:
    group: object
    a: tuple
    d: tuple


def aggregate_group_scores(residual):
    design = residual.design
    dimension = len(residual.z)
    groups = {group: ([Fraction(0)] * dimension, [Fraction(0)] * dimension)
              for group in design.groups}
    for i, group in enumerate(design.groups):
        a, d = groups[group]
        for j in range(dimension):
            a[j] += residual.z[j][i] * residual.y[i]
            d[j] += residual.z[j][i] * residual.x[i]
    return tuple(GroupAffineScore(group, tuple(groups[group][0]), tuple(groups[group][1]))
                 for group in sorted(groups, key=identity_key))


def evaluate_group_score(score, parameter):
    return tuple(a - parameter * d for a, d in zip(score.a, score.d))
