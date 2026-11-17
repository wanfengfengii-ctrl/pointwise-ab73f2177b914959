import unittest
from fractions import Fraction as F
from research import Archive
from research.scores.bundles import build_score_bundle
from research.inference.statistic import statistic_at
from research.inference.endpoints import sign_at_endpoint, compare_endpoints
from research.inference.polynomials import polynomial
from research.reports.sets import contains_parameter
from tests.test_records import row
from tests.test_cohorts import spec


def analyze(rows, threshold, z=("z",), w=()):
    with Archive() as app:
        app.apply("data", rows)
        frozen = app.freeze(spec([r["row_id"] for r in rows], z, w))["cohort_id"]
        bundle = build_score_bundle(app.read_cohort(frozen))
        report = app.execute(app.create_task(frozen, threshold))
        return bundle, report


class TestRankDropRegression(unittest.TestCase):
    # s_A(b) = (1, 0), s_B(b) = (0, b): S(b) = diag(1, b^2) drops rank at the
    # rational point 0, where T(0) = 1 while T(b) = 2 for every b != 0.
    rows = [row("a", y=1, x=0, z=1, z2=0, group="A"),
            row("b", y=0, x=-1, z=0, z2=1, group="B")]

    def test_singular_point_judged_by_actual_rank(self):
        bundle, report = analyze(self.rows, "3/2", ("z", "z2"))
        self.assertEqual(statistic_at(bundle, 0), 1)
        self.assertEqual(statistic_at(bundle, 1), 2)
        result = report.confidence_set
        self.assertEqual(result.intervals, [])
        self.assertEqual(result.points, [F(0)])
        self.assertTrue(contains_parameter(result, 0))
        self.assertFalse(contains_parameter(result, 1))

    def test_singular_point_at_threshold_and_above(self):
        _, report = analyze(self.rows, "1", ("z", "z2"))
        self.assertEqual(report.confidence_set.points, [F(0)])
        _, rejected = analyze(self.rows, "1/2", ("z", "z2"))
        self.assertEqual((rejected.confidence_set.intervals,
                          rejected.confidence_set.points), ([], []))

    def test_quartic_disconnected_with_embedded_rank_drop(self):
        # s(b) in {(b,0),(0,b),(1,0)}: T(b) = (b+1)^2/(b^2+1) + 1 for b != 0,
        # T(0) = 1; acceptance is b^2-4b+1 >= 0, two unbounded rays.
        rows = [row("a", y=0, x=-1, z=1, z2=0, group="A"),
                row("b", y=0, x=-1, z=0, z2=1, group="B"),
                row("c", y=1, x=0, z=1, z2=0, group="C")]
        bundle, report = analyze(rows, "5/2", ("z", "z2"))
        self.assertEqual(statistic_at(bundle, 0), 1)
        self.assertEqual(statistic_at(bundle, 2), F(14, 5))
        result = report.confidence_set
        self.assertEqual(result.points, [])
        self.assertEqual(len(result.intervals), 2)
        left, right = result.intervals
        self.assertIsNone(left.left)
        self.assertIsNone(right.right)
        self.assertTrue(left.right_closed and right.left_closed)
        for endpoint in (left.right, right.left):
            self.assertEqual(sign_at_endpoint(polynomial((1, -4, 1)), endpoint), 0)
        self.assertGreater(compare_endpoints(left.right, F(0)), 0)
        self.assertLess(compare_endpoints(left.right, F(1)), 0)
        self.assertGreater(compare_endpoints(right.left, F(3)), 0)
        self.assertLess(compare_endpoints(right.left, F(4)), 0)
        self.assertTrue(contains_parameter(result, 0))
        self.assertFalse(contains_parameter(result, 2))
        self.assertTrue(contains_parameter(result, -10**6))
        self.assertTrue(contains_parameter(result, 10**6))


class TestJointCoordinateRegression(unittest.TestCase):
    # Incident threshold 19/10: T(b) = 2 for every b in both coordinate
    # systems; the shear is an invertible rational tool transformation.
    original = [row("a", y=1, x=0, z=1, z2=0, group="A"),
                row("b", y=1, x=0, z=0, z2=1, group="B")]
    shear = [row("a", y=1, x=0, z=1, z2=0, group="A"),
             row("b", y=1, x=0, z=1, z2=1, group="B")]

    def test_invertible_tool_shear_keeps_empty_set(self):
        reports = [analyze(rows, "19/10", ("z", "z2")) for rows in (self.original, self.shear)]
        for bundle, report in reports:
            self.assertEqual(statistic_at(bundle, 0), 2)
            self.assertEqual(statistic_at(bundle, 2), 2)
            self.assertEqual((report.confidence_set.intervals,
                              report.confidence_set.points), ([], []))
        first, second = (report.audit for _, report in reports)
        self.assertEqual([g["a"] for g in first["groups"]],
                         [[F(1), F(0)], [F(0), F(1)]])
        self.assertEqual([g["a"] for g in second["groups"]],
                         [[F(1), F(0)], [F(1), F(1)]])

    def test_joint_coordinates_carried_into_audit(self):
        bundle, report = analyze(self.shear, "19/10", ("z", "z2"))
        self.assertEqual([s.a for s in bundle.scores], [(F(1), F(0)), (F(1), F(1))])
        self.assertEqual([s.d for s in bundle.scores], [(F(0), F(0)), (F(0), F(0))])
        self.assertEqual(report.audit["dimension"], 2)
        self.assertEqual([g["group"] for g in report.audit["groups"]], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
