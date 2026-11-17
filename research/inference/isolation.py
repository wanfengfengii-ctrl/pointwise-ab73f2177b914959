from dataclasses import dataclass
from fractions import Fraction
from .polynomials import (polynomial, primitive, square_free_part, poly_derivative,
                          poly_divmod, scale, evaluate, exact_divide)


@dataclass(frozen=True)
class RootIsolation:
    polynomial: tuple
    index: int
    lo: Fraction
    hi: Fraction
    exact: object = None


def sturm_sequence(a):
    a = square_free_part(a)
    if len(a) <= 1:
        return (a,) if a else ()
    result = [a, poly_derivative(a)]
    while result[-1]:
        remainder = poly_divmod(result[-2], result[-1])[1]
        if not remainder:
            break
        result.append(scale(remainder, -1))
    return tuple(result)


def variations(sequence, x):
    signs = []
    for p in sequence:
        value = evaluate(p, x)
        if value:
            signs.append(1 if value > 0 else -1)
    return sum(a != b for a, b in zip(signs, signs[1:]))


def count_real_roots(a, lo, hi):
    if lo >= hi or len(a) <= 1:
        return 0
    if evaluate(a, lo) == 0 or evaluate(a, hi) == 0:
        raise ValueError("root-count endpoints must not be roots")
    sequence = sturm_sequence(a)
    return variations(sequence, lo) - variations(sequence, hi)


def refine_root_interval(root, width=Fraction(1, 10**10)):
    if root.exact is not None:
        return root
    lo, hi, p = root.lo, root.hi, root.polynomial
    while hi-lo > width:
        middle = (lo+hi)/2
        if evaluate(p, middle) == 0:
            return RootIsolation(p, root.index, middle, middle, middle)
        if count_real_roots(p, lo, middle):
            hi = middle
        else:
            lo = middle
    return RootIsolation(p, root.index, lo, hi)


def _isolating_intervals(p):
    if len(p) <= 1:
        return []
    bound = Fraction(2 + max((abs(c/p[-1]).__ceil__() for c in p[:-1]), default=0))
    stack = [(-bound, bound)]
    output = []
    sequence = sturm_sequence(p)
    while stack:
        lo, hi = stack.pop()
        count = variations(sequence, lo) - variations(sequence, hi)
        if not count:
            continue
        if count == 1:
            output.append((lo, hi, None, p))
            continue
        middle = (lo+hi)/2
        if evaluate(p, middle) == 0:
            quotient = exact_divide(p, (-middle, Fraction(1)))
            return _isolating_intervals(quotient) + [(middle, middle, middle, p)]
        stack.extend([(middle, hi), (lo, middle)])
    return output


def isolate_real_roots(coefficients):
    p = primitive(square_free_part(polynomial(coefficients)))
    if len(p) <= 1:
        return ()
    # Rational-root theorem gives a denominator bound without divisor enumeration.
    denominator_bound = abs(int(p[-1]))
    target = min(Fraction(1, 10**10), Fraction(1, 4*denominator_bound**2))
    roots = []
    for lo, hi, exact, local in _isolating_intervals(p):
        root = RootIsolation(local, 0, lo, hi, exact)
        root = refine_root_interval(root, target)
        if root.exact is None:
            candidate = ((root.lo+root.hi)/2).limit_denominator(denominator_bound)
            if root.lo < candidate < root.hi and evaluate(p, candidate) == 0:
                root = RootIsolation(p, 0, candidate, candidate, candidate)
        roots.append(root)
    # Recursive rational-root removal may leave overlapping coarse enclosures.
    roots.sort(key=lambda r: (r.lo+r.hi)/2)
    while any(a.hi >= b.lo for a, b in zip(roots, roots[1:])):
        roots = [refine_root_interval(r, (r.hi-r.lo)/2) if r.exact is None else r
                 for r in roots]
        roots.sort(key=lambda r: (r.lo+r.hi)/2)
    return tuple(RootIsolation(p, i, r.lo, r.hi, r.exact) for i, r in enumerate(roots))
