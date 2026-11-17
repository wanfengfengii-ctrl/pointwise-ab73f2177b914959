from research.records.rows import dumps, loads


class CohortStore:
    def __init__(self, connection):
        self.connection = connection

    def initialize(self):
        self.connection.execute("""CREATE TABLE IF NOT EXISTS frozen_cohorts(
            cohort_id INTEGER PRIMARY KEY AUTOINCREMENT, body TEXT NOT NULL)""")
        self.connection.commit()

    def insert_frozen(self, body):
        cursor = self.connection.execute("INSERT INTO frozen_cohorts(body) VALUES(?)",
                                         (dumps(body),))
        return cursor.lastrowid

    def load_frozen(self, cohort_id):
        if isinstance(cohort_id, bool) or not isinstance(cohort_id, int):
            raise ValueError("invalid cohort identity")
        row = self.connection.execute("SELECT body FROM frozen_cohorts WHERE cohort_id=?",
                                      (cohort_id,)).fetchone()
        if row is None:
            raise KeyError("unknown cohort")
        return loads(row[0])

    def exists(self, cohort_id):
        try:
            self.load_frozen(cohort_id)
            return True
        except KeyError:
            return False
