from dataclasses import dataclass
from fractions import Fraction
from research.records.rows import normalize_rational
from research.inference.endpoints import (
    compare_endpoints, endpoint_payload, endpoint_from_payload)


@dataclass(frozen=True)
class Interval:
    left: object
    right: object
    left_closed: bool = False
    right_closed: bool = False


@dataclass
class ConfidenceSet:
    intervals: list
    points: list


def normalize_confidence_set(cells):
    pieces = []
    for decision in cells:
        if not decision.accepted:
            continue
        cell = decision.cell
        piece = Interval(cell.left, cell.right, cell.point, cell.point)
        if pieces:
            previous = pieces[-1]
            if (previous.right is not None and piece.left is not None
                    and compare_endpoints(previous.right, piece.left) == 0
                    and (previous.right_closed or piece.left_closed)):
                pieces[-1] = Interval(previous.left, piece.right, previous.left_closed,
                                      piece.right_closed)
                continue
        pieces.append(piece)
    intervals, points = [], []
    for piece in pieces:
        if (piece.left is not None and piece.right is not None
                and compare_endpoints(piece.left, piece.right) == 0):
            points.append(piece.left)
        else:
            intervals.append(piece)
    return ConfidenceSet(intervals, points)


def contains_parameter(confidence_set, parameter):
    parameter = normalize_rational(parameter)
    if any(compare_endpoints(p, parameter) == 0 for p in confidence_set.points):
        return True
    for interval in confidence_set.intervals:
        left = -1 if interval.left is None else compare_endpoints(interval.left, parameter)
        right = 1 if interval.right is None else compare_endpoints(interval.right, parameter)
        if (left < 0 or left == 0 and interval.left_closed) and (
                right > 0 or right == 0 and interval.right_closed):
            return True
    return False


def encode_confidence_set(confidence_set):
    return dict(intervals=[
        dict(left=endpoint_payload(i.left), right=endpoint_payload(i.right),
             left_closed=i.left_closed, right_closed=i.right_closed)
        for i in confidence_set.intervals],
        points=[endpoint_payload(p) for p in confidence_set.points])


def decode_confidence_set(payload):
    return ConfidenceSet([
        Interval(endpoint_from_payload(i["left"]), endpoint_from_payload(i["right"]),
                 i["left_closed"], i["right_closed"]) for i in payload["intervals"]],
        [endpoint_from_payload(p) for p in payload["points"]])
