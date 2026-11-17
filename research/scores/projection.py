from dataclasses import dataclass
from fractions import Fraction


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def independent_basis(columns):
    basis = []
    for column in columns:
        residual = list(column)
        for vector in basis:
            factor = dot(residual, vector) / dot(vector, vector)
            residual = [x - factor * y for x, y in zip(residual, vector)]
        if dot(residual, residual):
            basis.append(tuple(residual))
    return tuple(basis)


@dataclass(frozen=True)
class ResidualizedDesign:
    design: object
    y: tuple
    x: tuple
    z: tuple
    nuisance_rank: int
    tool_rank: int


def residualize_design(design):
    basis = independent_basis(design.w)
    def residual(column):
        output = list(column)
        for vector in basis:
            factor = dot(column, vector) / dot(vector, vector)
            output = [a - factor * b for a, b in zip(output, vector)]
        return tuple(output)
    z = tuple(residual(column) for column in design.z)
    return ResidualizedDesign(design, residual(design.y), residual(design.x), z,
                              len(basis), len(independent_basis(z)))
