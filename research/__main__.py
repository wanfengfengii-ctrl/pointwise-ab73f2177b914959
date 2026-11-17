import argparse
import json
import tempfile
from pathlib import Path
from . import Archive
from .records.rows import encode_value
from .reports.sets import encode_confidence_set, contains_parameter


def demo():
    examples = json.loads((Path(__file__).resolve().parent.parent / "samples.json").read_text())
    with tempfile.TemporaryDirectory(prefix="research-demo-") as directory:
        path = Path(directory) / "archive.sqlite"
        saved = {}
        with Archive(path) as app:
            for name, case in examples.items():
                app.apply(name, case["revisions"])
                cohort = app.freeze(case["spec"])["cohort_id"]
                task = app.create_task(cohort, case["threshold"])
                report = app.execute(task)
                saved[name] = (task, encode_confidence_set(report.confidence_set))
                print(json.dumps(encode_value(dict(example=name, task=task,
                      confidence_set=saved[name][1], audit=report.audit)), sort_keys=True))
            old_task = saved["disconnected"][0]
            assert not contains_parameter(app.read_report(old_task).confidence_set, 2)
            app.apply("correction", [dict(row_id="b", revision=2, payload=dict(
                values=dict(y=0,x=0,z=1), group="B"))])
            cohort = app.freeze(examples["disconnected"]["spec"])["cohort_id"]
            new_task = app.create_task(cohort, "3/2")
            new_report = app.execute(new_task)
            assert contains_parameter(new_report.confidence_set, 2)
            saved["corrected"] = (new_task, encode_confidence_set(new_report.confidence_set))
        with Archive(path) as app:
            for name, (task, expected) in saved.items():
                actual = encode_confidence_set(app.read_report(task).confidence_set)
                assert actual == expected, name
            print("REOPEN_OK: original and corrected research retained")


def main():
    parser = argparse.ArgumentParser(description="Exact frozen research archive")
    parser.add_argument("command", choices=["demo"])
    args = parser.parse_args()
    if args.command == "demo":
        demo()


if __name__ == "__main__":
    main()
