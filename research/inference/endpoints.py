from dataclasses import dataclass
from fractions import Fraction
from .polynomials import evaluate, poly_gcd, interval_evaluate
from .isolation import RootIsolation, refine_root_interval, count_real_roots

RationalEndpoint = Fraction


@dataclass(frozen=True)
class AlgebraicEndpoint:
    polynomial: tuple
    index: int
    lo: Fraction
    hi: Fraction

    def isolation(self):
        return RootIsolation(self.polynomial, self.index, self.lo, self.hi)


def from_isolation(root):
    if root.exact is not None:
        return root.exact
    return AlgebraicEndpoint(root.polynomial, root.index, root.lo, root.hi)


def endpoint_enclosure(endpoint):
    if isinstance(endpoint, Fraction):
        return endpoint, endpoint
    return endpoint.lo, endpoint.hi


def _refine(endpoint):
    root = endpoint.isolation()
    return from_isolation(refine_root_interval(root, (root.hi-root.lo)/2))


def compare_endpoints(left, right):
    while True:
        if isinstance(left, Fraction) and isinstance(right, Fraction):
            return (left > right) - (left < right)
        if isinstance(left, AlgebraicEndpoint) and isinstance(right, AlgebraicEndpoint):
            if left.polynomial == right.polynomial:
                return (left.index > right.index) - (left.index < right.index)
        ll, lh = endpoint_enclosure(left)
        rl, rh = endpoint_enclosure(right)
        if lh < rl:
            return -1
        if rh < ll:
            return 1
        if isinstance(left, Fraction):
            if evaluate(right.polynomial, left) == 0 and rl < left < rh:
                return 0
            right = _refine(right)
        elif isinstance(right, Fraction):
            if evaluate(left.polynomial, right) == 0 and ll < right < lh:
                return 0
            left = _refine(left)
        else:
            common = poly_gcd(left.polynomial, right.polynomial)
            lo, hi = max(ll, rl), min(lh, rh)
            if lo < hi and count_real_roots(common, lo, hi):
                return 0
            left, right = _refine(left), _refine(right)


def sign_at_endpoint(poly, endpoint):
    if not poly:
        return 0
    if isinstance(endpoint, Fraction):
        value = evaluate(poly, endpoint)
        return (value > 0) - (value < 0)
    common = poly_gcd(poly, endpoint.polynomial)
    if count_real_roots(common, endpoint.lo, endpoint.hi):
        return 0
    while True:
        lo, hi = interval_evaluate(poly, endpoint.lo, endpoint.hi)
        if lo > 0:
            return 1
        if hi < 0:
            return -1
        endpoint = _refine(endpoint)
        if isinstance(endpoint, Fraction):
            return sign_at_endpoint(poly, endpoint)


def endpoint_payload(endpoint):
    if endpoint is None:
        return None
    if isinstance(endpoint, Fraction):
        return dict(kind="rational", value=endpoint)
    return dict(kind="algebraic", polynomial=list(endpoint.polynomial), index=endpoint.index,
                isolation=[endpoint.lo, endpoint.hi])


def endpoint_from_payload(payload):
    if payload is None:
        return None
    if payload["kind"] == "rational":
        return Fraction(payload["value"])
    return AlgebraicEndpoint(tuple(payload["polynomial"]), payload["index"],
                             *payload["isolation"])


def rational_between(left, right):
    if left is None and right is None:
        return Fraction(0)
    if left is None:
        return endpoint_enclosure(right)[0] - 1
    if right is None:
        return endpoint_enclosure(left)[1] + 1
    if compare_endpoints(left, right) >= 0:
        raise ValueError("empty open cell")
    while True:
        upper = endpoint_enclosure(left)[1]
        lower = endpoint_enclosure(right)[0]
        if upper < lower:
            return (upper + lower)/2
        if isinstance(left, AlgebraicEndpoint):
            left = _refine(left)
        if isinstance(right, AlgebraicEndpoint):
            right = _refine(right)
