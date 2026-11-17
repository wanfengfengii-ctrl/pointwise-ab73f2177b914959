from research.records.rows import dumps, loads
from .sets import encode_confidence_set, decode_confidence_set


class ReportStore:
    def __init__(self, connection):
        self.connection = connection

    def initialize(self):
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS analysis_tasks(
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            binding TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('pending','success')));
        CREATE TABLE IF NOT EXISTS published_reports(
            task_id INTEGER PRIMARY KEY REFERENCES analysis_tasks(task_id),
            body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS score_audits(
            task_id INTEGER PRIMARY KEY REFERENCES analysis_tasks(task_id), body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS publication_receipts(
            task_id INTEGER PRIMARY KEY REFERENCES analysis_tasks(task_id), body TEXT NOT NULL);
        """)

    def insert_task(self, binding):
        return self.connection.execute(
            "INSERT INTO analysis_tasks(binding,state) VALUES(?,'pending')",
            (dumps(binding),)).lastrowid

    def load_task(self, task_id):
        if isinstance(task_id, bool) or not isinstance(task_id, int):
            raise ValueError("invalid task identity")
        row = self.connection.execute(
            "SELECT binding,state FROM analysis_tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError("unknown task")
        return loads(row[0]), row[1]

    def publish_complete(self, task_id, binding, confidence_set, audit, before_commit=None):
        receipt = dict(task_id=task_id, cohort_id=binding["cohort_id"], version=binding["version"])
        body = dict(task_id=task_id, binding=binding,
                    confidence_set=encode_confidence_set(confidence_set))
        self.connection.execute("INSERT INTO published_reports VALUES(?,?)", (task_id, dumps(body)))
        self.connection.execute("INSERT INTO score_audits VALUES(?,?)", (task_id, dumps(audit)))
        self.connection.execute("INSERT INTO publication_receipts VALUES(?,?)",
                                (task_id, dumps(receipt)))
        self.connection.execute("UPDATE analysis_tasks SET state='success' WHERE task_id=?", (task_id,))
        if before_commit is not None:
            before_commit()

    def load_published(self, task_id):
        binding, state = self.load_task(task_id)
        if state != "success":
            raise LookupError("report not ready")
        row = self.connection.execute(
            """SELECT r.body,a.body,p.body FROM published_reports r
            JOIN score_audits a USING(task_id) JOIN publication_receipts p USING(task_id)
            WHERE task_id=?""", (task_id,)).fetchone()
        if row is None:
            raise RuntimeError("incomplete archive")
        body, audit, receipt = (loads(v) for v in row)
        if body["binding"] != binding or audit["cohort_id"] != binding["cohort_id"]:
            raise RuntimeError("archive binding mismatch")
        body["confidence_set"] = decode_confidence_set(body["confidence_set"])
        body["audit"], body["receipt"] = audit, receipt
        return body
