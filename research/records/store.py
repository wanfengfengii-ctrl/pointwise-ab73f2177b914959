from .rows import dumps, loads
from .revisions import normalize_revision, revision_data


class RecordStore:
    def __init__(self, connection):
        self.connection = connection

    def initialize(self):
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS observation_history(
            row_key TEXT NOT NULL, revision TEXT NOT NULL, body TEXT NOT NULL,
            PRIMARY KEY(row_key, revision));
        CREATE TABLE IF NOT EXISTS observation_current(
            row_key TEXT PRIMARY KEY, revision TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS batch_receipts(
            batch_key TEXT PRIMARY KEY, request TEXT NOT NULL, receipt TEXT NOT NULL);
        """)

    def load_history(self, row_id, revision):
        row = self.connection.execute(
            "SELECT body FROM observation_history WHERE row_key=? AND revision=?",
            (dumps(row_id), str(revision))).fetchone()
        return None if row is None else normalize_revision(loads(row[0]))

    def load_current(self, row_id):
        row = self.connection.execute(
            """SELECT h.body FROM observation_current c JOIN observation_history h
            ON h.row_key=c.row_key AND h.revision=c.revision WHERE c.row_key=?""",
            (dumps(row_id),)).fetchone()
        return None if row is None else normalize_revision(loads(row[0]))

    def current_all(self):
        rows = self.connection.execute(
            """SELECT h.body FROM observation_current c JOIN observation_history h
            ON h.row_key=c.row_key AND h.revision=c.revision""").fetchall()
        return [normalize_revision(loads(r[0])) for r in rows]

    def load_receipt(self, batch_id):
        row = self.connection.execute(
            "SELECT request,receipt FROM batch_receipts WHERE batch_key=?",
            (dumps(batch_id),)).fetchone()
        return None if row is None else (row[0], loads(row[1]))

    def write_batch(self, batch_id, request, decisions, receipt):
        for decision in decisions:
            if not decision.insert:
                continue
            rev = decision.revision
            key = dumps(rev.row_id)
            self.connection.execute("INSERT INTO observation_history VALUES(?,?,?)",
                                    (key, str(rev.revision), dumps(revision_data(rev))))
            self.connection.execute(
                """INSERT INTO observation_current VALUES(?,?)
                ON CONFLICT(row_key) DO UPDATE SET revision=excluded.revision""",
                (key, str(rev.revision)))
        self.connection.execute("INSERT INTO batch_receipts VALUES(?,?,?)",
                                (dumps(batch_id), request, dumps(receipt)))
