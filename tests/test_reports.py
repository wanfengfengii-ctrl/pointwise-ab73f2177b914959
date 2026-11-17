import tempfile
import unittest
from pathlib import Path
from fractions import Fraction as F
from research import Archive
from research.reports.sets import encode_confidence_set, contains_parameter
from tests.test_records import row
from tests.test_cohorts import spec


def signature(report):
    return (report.task_id, report.binding, encode_confidence_set(report.confidence_set),
            report.audit, report.receipt)


def seed(app):
    app.apply("initial", [row("a", y=1, x=0, group="A"), row("b", y=0, x=-1, group="B")])
    cohort = app.freeze(spec(["a","b"]))["cohort_id"]
    return cohort, app.create_task(cohort, "3/2")


class TestReports(unittest.TestCase):
    def test_correction_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"research.sqlite"
            with Archive(path) as app:
                cohort, task = seed(app)
                old = signature(app.execute(task))
                frozen = app.read_cohort(cohort)
                app.apply("correction", [row("b", y=0, x=0, group="changed", revision=2)])
                new_cohort = app.freeze(spec(["a","b"]))["cohort_id"]
                new_task = app.create_task(new_cohort, "3/2")
                new = signature(app.execute(new_task))
                self.assertNotEqual(old[2], new[2])
                self.assertEqual(signature(app.read_report(task)), old)
                self.assertEqual(app.read_cohort(cohort), frozen)
            with Archive(path) as app:
                self.assertEqual(signature(app.read_report(task)), old)
                self.assertEqual(signature(app.read_report(new_task)), new)
                self.assertEqual(app.read_cohort(cohort), frozen)
                self.assertEqual(app.read_report(task).binding["threshold"], F(3,2))

    def test_publish_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"research.sqlite"
            with Archive(path) as app:
                cohort, task = seed(app)
                for stage in ("after_scores", "before_commit"):
                    def failure(current):
                        if current == stage:
                            raise ArithmeticError(stage)
                    with self.assertRaises(ArithmeticError):
                        app.execute(task, fault=failure)
                    with self.assertRaises(LookupError):
                        app.read_report(task)
                    self.assertEqual(app.reports.load_task(task)[1], "pending")
                    for table in ("published_reports","score_audits","publication_receipts"):
                        self.assertEqual(app.connection.execute(
                            "SELECT count(*) FROM " + table).fetchone()[0], 0)
            with Archive(path) as app:
                report = app.execute(task)
                self.assertEqual(len(report.confidence_set.intervals), 2)
                for table in ("published_reports","score_audits","publication_receipts"):
                    self.assertEqual(app.connection.execute(
                        "SELECT count(*) FROM " + table).fetchone()[0], 1)
                def forbidden(stage):
                    raise AssertionError("successful task recomputed")
                self.assertEqual(signature(app.execute(task, fault=forbidden)), signature(report))

    def test_read_isolation(self):
        with Archive() as app:
            cohort, task = seed(app)
            with self.assertRaises(LookupError):
                app.read_report(task)
            with self.assertRaises(KeyError):
                app.read_report(999)
            report = app.execute(task)
            before = signature(app.read_report(task))
            report.binding["roles"]["z"].append("changed")
            report.audit["groups"][0]["a"][0] = 999
            report.confidence_set.intervals.clear()
            report.receipt["cohort_id"] = -1
            self.assertEqual(signature(app.read_report(task)), before)
            payload = encode_confidence_set(app.read_report(task).confidence_set)
            payload["intervals"][0]["right"]["isolation"][0] = -999
            self.assertEqual(signature(app.read_report(task)), before)

    def test_task_binding(self):
        with Archive() as app:
            cohort, task = seed(app)
            before = app.connection.execute("SELECT count(*) FROM analysis_tasks").fetchone()[0]
            for value in (-1, True, 0.5, "bad"):
                with self.assertRaises(ValueError):
                    app.create_task(cohort, value)
            with self.assertRaises(KeyError):
                app.create_task(999, 1)
            self.assertEqual(app.connection.execute("SELECT count(*) FROM analysis_tasks").fetchone()[0],
                             before)
            self.assertEqual(app.reports.load_task(task)[1], "pending")
            app.apply("change", [row("a", y=9, revision=3)])
            self.assertEqual(app.reports.load_task(task)[0]["cohort_id"], cohort)
            self.assertFalse(contains_parameter(app.execute(task).confidence_set, 2))

    def test_failure_boundaries_in_memory(self):
        with Archive() as app:
            cohort, task = seed(app)
            for stage in ("after_scores","before_commit"):
                def failure(current):
                    if current == stage:
                        raise ArithmeticError(current)
                with self.assertRaises(ArithmeticError):
                    app.execute(task,fault=failure)
                self.assertEqual(app.reports.load_task(task)[1],"pending")
                with self.assertRaises(LookupError):
                    app.read_report(task)
                for table in ("published_reports","score_audits","publication_receipts"):
                    self.assertEqual(app.connection.execute(
                        "SELECT count(*) FROM " + table).fetchone()[0],0)
            report = app.execute(task)
            def forbidden(stage):
                raise AssertionError("successful task recomputed")
            self.assertEqual(signature(app.execute(task,fault=forbidden)),signature(report))
