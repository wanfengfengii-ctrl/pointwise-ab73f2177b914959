from dataclasses import dataclass
from fractions import Fraction
from research.scores.bundles import validate_score_bundle
from .statistic import validate_threshold, score_moments, matrix_rank
from .polynomials import polynomial
from .isolation import isolate_real_roots
from .endpoints import from_isolation, sign_at_endpoint, rational_between


@dataclass(frozen=True)
class RankCell:
    left: object
    right: object
    point: bool = False


@dataclass(frozen=True)
class AcceptanceCell:
    cell: RankCell
    accepted: bool


def _reference_quadratic(bundle, threshold):
    validate_score_bundle(bundle)
    _, matrix = score_moments(bundle, Fraction(0))
    rank = matrix_rank(matrix)
    def value(parameter):
        q = [sum((s.a[j] - parameter * s.d[j] for s in bundle.scores), Fraction(0))
             for j in range(bundle.dimension)]
        if rank == 0:
            statistic = Fraction(0)
        elif len(q) == 1:
            statistic = q[0] ** 2 / matrix[0][0]
        else:
            a, cross, d = matrix[0][0], matrix[0][1], matrix[1][1]
            if rank == 2:
                statistic = (d*q[0]**2 - 2*cross*q[0]*q[1] + a*q[1]**2) / (a*d-cross**2)
            else:
                statistic = (a*q[0]**2 + 2*cross*q[0]*q[1] + d*q[1]**2) / (a+d)**2
        return statistic - threshold
    center, plus, minus = value(Fraction(0)), value(Fraction(1)), value(Fraction(-1))
    return polynomial((center, (plus-minus)/2, (plus+minus)/2-center))


def build_rank_events(bundle, threshold):
    threshold = validate_threshold(threshold)
    boundary = _reference_quadratic(bundle, threshold)
    return tuple(from_isolation(root) for root in isolate_real_roots(boundary))


def partition_rank_cells(events):
    cells = []
    previous = None
    for endpoint in events:
        cells.append(RankCell(previous, endpoint))
        cells.append(RankCell(endpoint, endpoint, True))
        previous = endpoint
    cells.append(RankCell(previous, None))
    return tuple(cells)


def infer_acceptance_cells(bundle, threshold):
    threshold = validate_threshold(threshold)
    boundary = _reference_quadratic(bundle, threshold)
    events = build_rank_events(bundle, threshold)
    output = []
    for cell in partition_rank_cells(events):
        parameter = cell.left if cell.point else rational_between(cell.left, cell.right)
        output.append(AcceptanceCell(cell, sign_at_endpoint(boundary, parameter) <= 0))
    return tuple(output)
