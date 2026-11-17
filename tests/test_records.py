import unittest
from fractions import Fraction
from research import Archive


def row(row_id, y=0, x=1, z=1, group="A", revision=1, **columns):
    values = dict(y=y, x=x, z=z, **columns)
    return dict(row_id=row_id, revision=revision,
                payload=dict(values=values, group=group))


def table_snapshot(app):
    return {name: app.connection.execute("SELECT * FROM " + name + " ORDER BY 1,2").fetchall()
            for name in ("observation_history", "observation_current", "batch_receipts")}


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.app = Archive()
        self.addCleanup(self.app.close)

    def test_conflicting_batch(self):
        app = self.app
        original = app.apply("initial", [row("a"), row("b")])
        before = table_snapshot(app)
        with self.assertRaises(ValueError):
            app.apply("bad", [row("a", y=9, revision=2), row("b", y=8)])
        self.assertEqual(table_snapshot(app), before)
        app.apply("later", [row("a", y=7, revision=3)])
        self.assertEqual(app.apply("initial", [row("b"), row("a")]), original)
        self.assertEqual(app.records.load_current("a").revision, 3)
        self.assertIsNone(app.records.load_receipt("bad"))

    def test_semantic_replay(self):
        app = self.app
        receipt = app.apply(1, [row(1, y="2/6")])
        self.assertEqual(app.apply(1, [row(1, y=Fraction(1, 3))]), receipt)
        with self.assertRaises(ValueError):
            app.apply(1, [row(1, y=2)])
        with self.assertRaises(ValueError):
            app.apply(2, [row(1, y=2)])
        app.apply(3, [row(1, y=4, revision=4)])
        replay = app.apply(4, [row(1, y="1/3")])
        self.assertEqual(replay["replayed"], [[1, 1]])
        self.assertEqual(app.records.load_current(1).revision, 4)
        before = table_snapshot(app)
        with self.assertRaises(ValueError):
            app.apply(5, [row("new"), row(1, revision=2)])
        self.assertEqual(table_snapshot(app), before)
        self.assertEqual(app.records.load_current(1).payload.values["y"], 4)

    def test_invalid_and_input_copy(self):
        for value in (True, 0.1, "1/0", "bad"):
            before = table_snapshot(self.app)
            with self.assertRaises(ValueError):
                self.app.apply("bad", [row("x", y=value)])
            self.assertEqual(table_snapshot(self.app), before)
        value = row("a", y="1/3", group=1)
        self.app.apply("ok", [value])
        value["payload"]["values"]["y"] = 99
        self.assertEqual(self.app.records.load_current("a").payload.values["y"], Fraction(1, 3))
        with self.assertRaises(ValueError):
            self.app.apply("duplicate", [row("a", revision=2), row("a", revision=3)])

    def test_unbounded_revision_identity(self):
        revision = 10**40
        self.app.apply("large", [row(10**30, revision=revision)])
        self.assertEqual(self.app.records.load_current(10**30).revision, revision)
        self.assertEqual(self.app.records.load_history(10**30, revision).revision, revision)
