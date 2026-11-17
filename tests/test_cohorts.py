import unittest
from research import Archive
from tests.test_records import row


def spec(ids, z=("z",), w=()):
    return dict(row_ids=list(ids), y="y", x="x", z=list(z), w=list(w))


class TestCohorts(unittest.TestCase):
    def setUp(self):
        self.app = Archive()
        self.addCleanup(self.app.close)

    def test_freeze_complete_rows(self):
        rows = [row("ok", group=1), row("missing", z=None), row("ungrouped", group=None),
                row("withdrawn"), row("nuisance", w=None)]
        for r in rows[:-1]:
            r["payload"]["values"]["w"] = 0
        rows[3]["payload"]["withdrawn"] = True
        self.app.apply("source", rows)
        receipt = self.app.freeze(spec(["not_found"] + [r["row_id"] for r in rows], w=("w",)))
        self.assertEqual(receipt["adopted"], [dict(row_id="ok", revision=1, group=1)])
        reasons = {r["row_id"]: r["reason"] for r in receipt["excluded"]}
        self.assertEqual(reasons, dict(not_found="not_found", missing="missing:z",
                                      ungrouped="missing_group", withdrawn="withdrawn",
                                      nuisance="missing:w"))
        frozen = self.app.read_cohort(receipt["cohort_id"])
        self.assertEqual(len(frozen.rows), 1)
        self.assertEqual(frozen.rows[0]["payload"]["group"], 1)
        other = self.app.freeze(spec(list(reversed(["not_found"] + [r["row_id"] for r in rows])),
                                     w=("w",)))
        self.assertEqual(receipt["adopted"], other["adopted"])
        self.assertEqual(receipt["excluded"], other["excluded"])

    def test_invalid_role(self):
        self.app.apply(1, [row("a", w=1, w2=2, w3=3, w4=4, w5=5)])
        invalid = [spec(["a"], z=("unknown",)), spec(["a"], z=("y",)),
                   spec(["a"], z=("z", "w", "w2")),
                   spec(["a"], w=("w", "w2", "w3", "w4", "w5")),
                   spec(list(range(25))), spec(["a", "a"])]
        before = self.app.connection.execute("SELECT count(*) FROM frozen_cohorts").fetchone()
        for s in invalid:
            with self.assertRaises(ValueError):
                self.app.freeze(s)
            self.assertEqual(self.app.connection.execute(
                "SELECT count(*) FROM frozen_cohorts").fetchone(), before)
        self.app.apply(2, [row(i, group=i) for i in range(9)])
        with self.assertRaises(ValueError):
            self.app.freeze(spec(list(range(9))))
        self.assertEqual(self.app.records.load_current("a").revision, 1)

    def test_withdraw_restore_and_frozen_copy(self):
        self.app.apply(1, [row("a", y=2, group="old")])
        first = self.app.freeze(spec(["a"]))["cohort_id"]
        value = self.app.read_cohort(first)
        value.rows[0]["payload"]["values"]["y"] = 99
        withdrawn = row("a", revision=2)
        withdrawn["payload"]["withdrawn"] = True
        self.app.apply(2, [withdrawn])
        second = self.app.freeze(spec(["a"]))["cohort_id"]
        self.assertEqual(self.app.read_cohort(second).rows, ())
        self.app.apply(3, [row("a", y=7, group="new", revision=3)])
        third = self.app.freeze(spec(["a"]))["cohort_id"]
        self.assertEqual(self.app.read_cohort(first).rows[0]["payload"]["values"]["y"], 2)
        self.assertEqual(self.app.read_cohort(first).rows[0]["payload"]["group"], "old")
        self.assertEqual(self.app.read_cohort(third).rows[0]["revision"], 3)
