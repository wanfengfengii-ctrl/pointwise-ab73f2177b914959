from dataclasses import dataclass
from fractions import Fraction
from research.scores.bundles import validate_score_bundle
from .statistic import validate_threshold
from .polynomials import polynomial, poly_add, poly_multiply, scale, subtract
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


@dataclass(frozen=True)
class BoundaryPolynomials:
    # boundary(b) <= 0 decides acceptance at every parameter of full tool rank.
    boundary: tuple
    # Real roots of rank_drop are the singular parameters; () when none can
    # exist or when every parameter is singular (boundary then decides all).
    rank_drop: tuple
    # rank_one(b) <= 0 decides acceptance at singular parameters, where the
    # statistic uses the Moore-Penrose inverse of the actual rank at that point.
    rank_one: tuple


def _score_polynomials(bundle):
    """Affine q(b) coordinates and quadratic S(b) entries as exact polynomials."""
    validate_score_bundle(bundle)
    k = bundle.dimension
    q = []
    for j in range(k):
        constant = sum((s.a[j] for s in bundle.scores), Fraction(0))
        linear = sum((s.d[j] for s in bundle.scores), Fraction(0))
        q.append(polynomial((constant, -linear)))
    entries = [[polynomial(()) for _ in range(k)] for _ in range(k)]
    for score in bundle.scores:
        coords = [polynomial((score.a[j], -score.d[j])) for j in range(k)]
        for i in range(k):
            for j in range(k):
                entries[i][j] = poly_add(entries[i][j],
                                         poly_multiply(coords[i], coords[j]))
    return q, entries


def boundary_polynomials(bundle, threshold):
    """Exact acceptance polynomials with the covariance varying in b.

    The statistic is T(b) = q(b)' S(b)+ q(b) with S(b) = sum of s_g(b)s_g(b)'.
    Clearing the positive denominators gives polynomial decision rules:
    dimension 1: P = q^2 - c*S decides everywhere, since S(b) = 0 forces
        q(b) = 0 and both the statistic and P vanish there.
    dimension 2, det S not identically zero: P = q' adj(S) q - c*det(S)
        decides full-rank parameters.  Singular parameters are real roots of
        det(S); q(b) lies in range S(b) there, so they are also roots of P and
        are judged by R = q' S q - c*(tr S)^2 with the actual rank at the point.
    dimension 2, det S identically zero: R decides everywhere (R = 0 exactly
        where the statistic is zero or equals c).
    dimension 0: the statistic is identically zero.
    """
    threshold = validate_threshold(threshold)
    q, s = _score_polynomials(bundle)
    if not q:
        return BoundaryPolynomials((), (), ())
    if len(q) == 1:
        boundary = subtract(poly_multiply(q[0], q[0]), scale(s[0][0], threshold))
        return BoundaryPolynomials(boundary, (), ())
    trace = poly_add(s[0][0], s[1][1])
    rank_one = subtract(
        poly_add(poly_add(poly_multiply(poly_multiply(q[0], q[0]), s[0][0]),
                          poly_multiply(poly_multiply(q[1], q[1]), s[1][1])),
                 scale(poly_multiply(poly_multiply(q[0], q[1]), s[0][1]), 2)),
        scale(poly_multiply(trace, trace), threshold))
    det = subtract(poly_multiply(s[0][0], s[1][1]),
                   poly_multiply(s[0][1], s[0][1]))
    if not det:
        return BoundaryPolynomials(rank_one, (), ())
    adjoint = poly_add(
        poly_add(poly_multiply(poly_multiply(q[0], q[0]), s[1][1]),
                 poly_multiply(poly_multiply(q[1], q[1]), s[0][0])),
        scale(poly_multiply(poly_multiply(q[0], q[1]), s[0][1]), -2))
    boundary = subtract(adjoint, scale(det, threshold))
    return BoundaryPolynomials(boundary, det, rank_one)


def build_rank_events(bundle, threshold):
    polys = boundary_polynomials(bundle, threshold)
    return tuple(from_isolation(root) for root in isolate_real_roots(polys.boundary))


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
    polys = boundary_polynomials(bundle, threshold)
    events = tuple(from_isolation(root) for root in isolate_real_roots(polys.boundary))
    output = []
    for cell in partition_rank_cells(events):
        if cell.point:
            parameter = cell.left
            decision = polys.boundary
            if polys.rank_drop and sign_at_endpoint(polys.rank_drop, parameter) == 0:
                decision = polys.rank_one
        else:
            parameter = rational_between(cell.left, cell.right)
            decision = polys.boundary
        output.append(AcceptanceCell(cell, sign_at_endpoint(decision, parameter) <= 0))
    return tuple(output)
