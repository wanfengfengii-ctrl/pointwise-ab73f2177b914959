from dataclasses import dataclass
from fractions import Fraction
from research.records.rows import normalize_rational
from research.scores.groups import evaluate_group_score
from research.scores.bundles import validate_score_bundle

TEST_VERSION = "group-ar-v1"


def validate_threshold(value):
    value = normalize_rational(value)
    if value < 0:
        raise ValueError("negative threshold")
    return value


@dataclass(frozen=True)
class TestSpecification:
    threshold: Fraction
    version: str = TEST_VERSION

    def __post_init__(self):
        object.__setattr__(self, "threshold", validate_threshold(self.threshold))
        if self.version != TEST_VERSION:
            raise ValueError("unsupported test version")


def score_moments(bundle, parameter):
    validate_score_bundle(bundle)
    k = bundle.dimension
    q = [Fraction(0)] * k
    matrix = [[Fraction(0) for _ in range(k)] for _ in range(k)]
    for score in bundle.scores:
        vector = evaluate_group_score(score, parameter)
        for i in range(k):
            q[i] += vector[i]
            for j in range(k):
                matrix[i][j] += vector[i] * vector[j]
    return q, matrix


def matrix_rank(matrix):
    if not matrix:
        return 0
    if len(matrix) == 1:
        return int(matrix[0][0] != 0)
    a, b, d = matrix[0][0], matrix[0][1], matrix[1][1]
    return 2 if a * d - b * b else int(a + d != 0)


def statistic_at(bundle, parameter):
    parameter = normalize_rational(parameter)
    q, matrix = score_moments(bundle, parameter)
    rank = matrix_rank(matrix)
    if rank == 0:
        return Fraction(0)
    if len(q) == 1:
        return q[0] ** 2 / matrix[0][0]
    a, b, d = matrix[0][0], matrix[0][1], matrix[1][1]
    if rank == 2:
        return (d*q[0]**2 - 2*b*q[0]*q[1] + a*q[1]**2) / (a*d - b*b)
    return (a*q[0]**2 + 2*b*q[0]*q[1] + d*q[1]**2) / (a+d)**2
