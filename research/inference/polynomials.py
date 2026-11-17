from fractions import Fraction
from math import gcd, lcm

# Coefficients are in ascending powers; () is the zero polynomial.
Polynomial = tuple


def polynomial(coefficients=()):
    result = [Fraction(c) for c in coefficients]
    while result and result[-1] == 0:
        result.pop()
    return tuple(result)


def poly_add(a, b):
    return polynomial((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)
                      for i in range(max(len(a), len(b))))


def scale(a, factor):
    return polynomial(c * factor for c in a)


def subtract(a, b):
    return poly_add(a, scale(b, -1))


def poly_multiply(a, b):
    if not a or not b:
        return ()
    result = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i+j] += x*y
    return polynomial(result)


def evaluate(a, value):
    result = Fraction(0)
    for coefficient in reversed(a):
        result = result * value + coefficient
    return result


def poly_derivative(a):
    return polynomial(i * a[i] for i in range(1, len(a)))


def poly_divmod(a, b):
    if not b:
        raise ZeroDivisionError("zero polynomial")
    remainder = list(polynomial(a))
    quotient = [Fraction(0)] * max(0, len(a)-len(b)+1)
    while remainder and len(remainder) >= len(b):
        offset = len(remainder)-len(b)
        factor = remainder[-1]/b[-1]
        quotient[offset] = factor
        for i, c in enumerate(b):
            remainder[offset+i] -= factor*c
        while remainder and not remainder[-1]:
            remainder.pop()
    return polynomial(quotient), polynomial(remainder)


def exact_divide(a, b):
    quotient, remainder = poly_divmod(a, b)
    if remainder:
        raise ArithmeticError("inexact polynomial division")
    return quotient


def monic(a):
    return scale(a, 1/a[-1]) if a else ()


def poly_gcd(a, b):
    while b:
        a, b = b, poly_divmod(a, b)[1]
    return monic(a)


def square_free_part(a):
    a = polynomial(a)
    return monic(exact_divide(a, poly_gcd(a, poly_derivative(a)))) if len(a) > 1 else monic(a)


def primitive(a):
    a = polynomial(a)
    if not a:
        return ()
    denominator = lcm(*(c.denominator for c in a))
    integers = [int(c * denominator) for c in a]
    divisor = gcd(*integers)
    if integers[-1] < 0:
        divisor = -divisor
    return tuple(Fraction(c // divisor) for c in integers)


def extract_rational_roots(a):
    from .isolation import isolate_real_roots
    return tuple(r.exact for r in isolate_real_roots(a) if r.exact is not None)


def interval_evaluate(a, lo, hi):
    lower = upper = Fraction(0)
    for coefficient in reversed(a):
        products = (lower*lo, lower*hi, upper*lo, upper*hi)
        lower, upper = min(products)+coefficient, max(products)+coefficient
    return lower, upper
