import unittest
from fractions import Fraction as F
from research import Archive
from research.scores.bundles import build_score_bundle
from research.inference.statistic import statistic_at, score_moments, matrix_rank
from research.inference.isolation import isolate_real_roots, count_real_roots
from research.inference.polynomials import (polynomial, poly_multiply, extract_rational_roots,
                                           evaluate)
from research.inference.endpoints import (AlgebraicEndpoint, compare_endpoints,
                                         endpoint_enclosure, from_isolation, sign_at_endpoint)
from research.reports.sets import contains_parameter
from tests.test_records import row
from tests.test_cohorts import spec


def analyze(rows, threshold, z=("z",), w=()):
    with Archive() as app:
        app.apply("data", rows)
        frozen = app.freeze(spec([r["row_id"] for r in rows], z, w))["cohort_id"]
        bundle = build_score_bundle(app.read_cohort(frozen))
        report = app.execute(app.create_task(frozen, threshold))
        return bundle, report.confidence_set


class TestInference(unittest.TestCase):
    def test_singleton(self):
        bundle, result = analyze([row("a")], "1/2")
        self.assertEqual(result.intervals, [])
        self.assertEqual(result.points, [F(0)])
        self.assertEqual(statistic_at(bundle, 0), 0)
        for b in (F(-1, 1000), F(1, 1000)):
            self.assertEqual(statistic_at(bundle, b), 1)
            self.assertFalse(contains_parameter(result, b))
        _, third = analyze([row("a", y="1/3")], "1/2")
        self.assertEqual(third.points, [F(1, 3)])

    def test_joint_coordinates(self):
        original = [row("a", y=1, x=0, z=1, z2=0, group="A"),
                    row("b", y=1, x=0, z=0, z2=1, group="B")]
        shear = [row("a", y=1, x=0, z=1, z2=0, group="A"),
                 row("b", y=1, x=0, z=1, z2=1, group="B")]
        for rows in (original, shear):
            bundle, result = analyze(rows, "5/2", ("z", "z2"))
            self.assertEqual(statistic_at(bundle, 0), 2)
            self.assertTrue(contains_parameter(result, 100))
            self.assertEqual(len(result.intervals), 1)
            self.assertIsNone(result.intervals[0].left)
            self.assertIsNone(result.intervals[0].right)
            self.assertEqual(matrix_rank(score_moments(bundle, 0)[1]), 2)
        for redundant in (False, True):
            rows = [row("a", y=1, x=0, z=1, w=1, w2=2, group="A"),
                    row("b", y=2, x=0, z=0, w=1, w2=2, group="B")]
            bundle, result = analyze(rows, "3/2", w=("w", "w2") if redundant else ("w",))
            self.assertEqual([s.a for s in bundle.scores], [(F(-1,4),), (F(-1,4),)])
            self.assertEqual(statistic_at(bundle, 0), 2)
            self.assertEqual((result.intervals, result.points), ([], []))
            self.assertEqual(bundle.nuisance_rank, 1)

    def test_group_permutation(self):
        rows = [row("a", y=1, x=0, group="A"), row("c", y=2, x=0, group="A"),
                row("b", y=3, x=0, group="B"), row("d", y=4, x=0, group="B")]
        for ordered in (rows, list(reversed(rows))):
            bundle, result = analyze(ordered, "9/5")
            self.assertEqual([s.a for s in bundle.scores], [(F(3),), (F(7),)])
            self.assertEqual(statistic_at(bundle, 0), F(50,29))
            self.assertTrue(contains_parameter(result, 0))
            self.assertEqual(bundle.row_groups, ("A", "B", "A", "B"))

    def test_disconnected_and_algebraic(self):
        rows = [row("a", y=1, x=0, group="A"), row("b", y=0, x=-1, group="B")]
        bundle, result = analyze(rows, "3/2")
        self.assertEqual(result.points, [])
        self.assertEqual(len(result.intervals), 2)
        left, right = result.intervals
        self.assertIsNone(left.left)
        self.assertIsNone(right.right)
        self.assertTrue(left.right_closed and right.left_closed)
        bounds = [(F(267949192,10**9), F(267949193,10**9)),
                  (F(3732050807,10**9), F(3732050808,10**9))]
        for endpoint, (lo, hi) in zip((left.right, right.left), bounds):
            self.assertIsInstance(endpoint, AlgebraicEndpoint)
            self.assertGreater(compare_endpoints(endpoint, lo), 0)
            self.assertLess(compare_endpoints(endpoint, hi), 0)
            enclosure = endpoint_enclosure(endpoint)
            self.assertLessEqual(enclosure[1]-enclosure[0], F(1,10**8))
            self.assertEqual(sign_at_endpoint(polynomial((1,-4,1)), endpoint), 0)
        self.assertFalse(contains_parameter(result, 2))
        self.assertTrue(contains_parameter(result, -1000000))
        self.assertTrue(contains_parameter(result, 1000000))
        self.assertEqual(statistic_at(bundle, 2), F(9,5))

    def test_rank_zero_and_boundary(self):
        for rows, z in (([row("a", y=0, x=0)], ("z",)),
                        ([row("a")], ()),
                        ([row("a", z=0)], ("z",))):
            _, result = analyze(rows, 0, z)
            self.assertEqual(len(result.intervals), 1)
            self.assertTrue(contains_parameter(result, 99999999))
        for threshold, accepted in ((F(1,2), False), (F(1), True)):
            _, result = analyze([row("a", y=1, x=0)], threshold)
            self.assertEqual(contains_parameter(result, 0), accepted)
        rows = [row("a", y=1, x=0, group="A"), row("b", y=0, x=1, group="B")]
        _, result = analyze(rows, 1)
        self.assertEqual(len(result.intervals), 1)
        self.assertEqual(result.intervals[0].left, 0)
        self.assertTrue(result.intervals[0].left_closed)
        self.assertIsNone(result.intervals[0].right)
        self.assertFalse(contains_parameter(result, -1))

    def test_persistent_rank_one_and_variable_rank(self):
        scalar = [row("a", y=1, x=0, group="A"), row("b", y=0, x=-1, group="B")]
        joint = [row("a", y=1, x=0, z2=2, group="A"),
                 row("b", y=0, x=-1, z2=2, group="B")]
        one, set_one = analyze(scalar, "3/2")
        two, set_two = analyze(joint, "3/2", ("z","z2"))
        for b in (F(-7), F(0), F(1,3), F(2), F(9)):
            self.assertEqual(statistic_at(one, b), statistic_at(two, b))
            self.assertEqual(contains_parameter(set_one, b), contains_parameter(set_two, b))
        for a, b in zip(set_one.intervals, set_two.intervals):
            for x, y in ((a.left,b.left), (a.right,b.right)):
                self.assertTrue(x is y is None or compare_endpoints(x,y) == 0)
        rows = [row("a", y=1, x=0, z=1, z2=0, group="A"),
                row("b", y=0, x=1, z=0, z2=1, group="B")]
        bundle, result = analyze(rows, "3/2", ("z", "z2"))
        self.assertEqual(result.points, [F(0)])
        self.assertEqual(result.intervals, [])
        self.assertEqual(statistic_at(bundle, 0), 1)
        self.assertEqual(statistic_at(bundle, 1), 2)

    def test_exact_root_identity(self):
        p = polynomial((1,-4,1))
        q = poly_multiply(p, polynomial((-10,1)))
        r1 = [from_isolation(r) for r in isolate_real_roots(p)]
        r2 = [from_isolation(r) for r in isolate_real_roots(q)]
        self.assertEqual(compare_endpoints(r1[0], r2[0]), 0)
        self.assertEqual(compare_endpoints(r1[1], r2[1]), 0)
        repeated = poly_multiply(polynomial((-F(1,3),1)), polynomial((-F(1,3),1)))
        mixed = poly_multiply(repeated, polynomial((0,1)))
        self.assertEqual(extract_rational_roots(mixed), (F(0),F(1,3)))
        self.assertEqual(count_real_roots(p, F(0),F(4)), 2)
        self.assertEqual(isolate_real_roots(()), ())
        self.assertEqual(isolate_real_roots((1,)), ())
        self.assertEqual(isolate_real_roots((1,0,1)), ())

    def test_deterministic_pointwise_oracle(self):
        # Independent projection-of-ones identity for 1/2-dimensional group matrices.
        for seed in range(12):
            rows = [row(i, y=(seed+2*i)%7-3, x=(seed*i+1)%5-2,
                        z=(i+seed)%3-1, z2=(2*i+seed)%5-2, group=i%3)
                    for i in range(5)]
            bundle, result = analyze(rows, F(4,3), ("z","z2"))
            for parameter in (F(-3), F(-1,3), F(0), F(2,5), F(4)):
                vectors = [tuple(a-parameter*d for a,d in zip(s.a,s.d)) for s in bundle.scores]
                columns = [tuple(v[j] for v in vectors) for j in range(2)]
                basis = []
                for column in columns:
                    vector = list(column)
                    for old in basis:
                        factor = sum(a*b for a,b in zip(vector,old))/sum(a*a for a in old)
                        vector = [a-factor*b for a,b in zip(vector,old)]
                    if any(vector):
                        basis.append(vector)
                independent = sum((sum(v)**2/sum(a*a for a in v) for v in basis), F(0))
                self.assertEqual(statistic_at(bundle, parameter), independent)
                self.assertEqual(contains_parameter(result, parameter), independent <= F(4,3))

    def test_projection_shear_and_redundancy(self):
        rows = [row(i, y=(i*i+2)%7, x=(i+1)%3-1, z=i%3-1,
                    z2=(2*i)%5-2, w=1, w2=2, group=i%3) for i in range(6)]
        transformed = []
        for r in reversed(rows):
            values = r["payload"]["values"].copy()
            a, b = values["z"], values["z2"]
            values["z"], values["z2"] = 2*a+b, a+b
            transformed.append(dict(row_id=r["row_id"], revision=1,
                                    payload=dict(values=values, group=r["payload"]["group"])))
        base, first = analyze(rows, "3/2", ("z","z2"), ("w",))
        changed, second = analyze(transformed, "3/2", ("z","z2"), ("w","w2"))
        self.assertEqual(changed.nuisance_rank, 1)
        self.assertEqual(len(first.points), len(second.points))
        self.assertEqual(len(first.intervals), len(second.intervals))
        for a,b in zip(first.points,second.points):
            self.assertEqual(compare_endpoints(a,b),0)
        for a,b in zip(first.intervals,second.intervals):
            self.assertEqual((a.left_closed,a.right_closed),(b.left_closed,b.right_closed))
            for x,y in ((a.left,b.left),(a.right,b.right)):
                self.assertTrue(x is y is None or compare_endpoints(x,y) == 0)
        for parameter in (F(-10),F(-1,3),F(0),F(1,2),F(12)):
            self.assertEqual(statistic_at(base,parameter),statistic_at(changed,parameter))

    def test_empty_and_projected_zero(self):
        with Archive() as app:
            app.apply(1,[row("a",y=None,w=1)])
            cohort = app.freeze(spec(["a"]))["cohort_id"]
            report = app.execute(app.create_task(cohort,0))
            self.assertEqual(report.audit["row_revisions"],[])
            self.assertTrue(contains_parameter(report.confidence_set,0))
            self.assertTrue(contains_parameter(report.confidence_set,10**20))
        bundle, result = analyze([row("a",y=7,w=1)],0,w=("w",))
        self.assertEqual(bundle.tool_rank,0)
        self.assertEqual(bundle.scores[0].a,(F(0),))
        self.assertTrue(contains_parameter(result,-10**20))

    def test_algebraic_rank_drop_point(self):
        rows = [
            row("a1",y=0,x=-1,z=1,z2=0,group="A"),
            row("a2",y=1,x=0,z=0,z2=1,group="A"),
            row("b1",y=2,x=0,z=1,z2=0,group="B"),
            row("b2",y=0,x=-1,z=0,z2=1,group="B")]
        _, result = analyze(rows,"1/2",("z","z2"))
        self.assertEqual(result.intervals,[])
        self.assertEqual(len(result.points),1)
        point = result.points[0]
        self.assertIsInstance(point,AlgebraicEndpoint)
        self.assertEqual(sign_at_endpoint(polynomial((-2,0,1)),point),0)
        self.assertLess(compare_endpoints(point,F(-1)),0)
        self.assertGreater(compare_endpoints(point,F(-2)),0)
