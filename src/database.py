from datetime import datetime
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "firemind_gtm.db"


class conn:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.execute("PRAGMA foreign_keys = ON;")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def get_connection(self):
        return self._connection

    def cursor(self):
        return self._connection.cursor()

    def execute(self, query, params=()):
        return self._connection.execute(query, params)

    def executemany(self, query, seq_of_params):
        return self._connection.executemany(query, seq_of_params)

    def executescript(self, script):
        return self._connection.executescript(script)

    def commit(self):
        self._connection.commit()

    def close(self):
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def create_tables(self):
        self.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL UNIQUE,
                sector TEXT NOT NULL,
                subsector TEXT,
                hq_country TEXT,
                employee_count INTEGER,
                revenue_gbp REAL,
                website TEXT,
                linkedin_url TEXT,
                public_private TEXT,
                cloud_environment TEXT,
                it_complexity_notes TEXT,
                fsi_priority_segment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sources (
                source_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_title TEXT,
                url TEXT NOT NULL,
                publisher TEXT,
                published_date DATE,
                retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                snippet TEXT,
                reliability TEXT
            );

            CREATE TABLE IF NOT EXISTS signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                signal_type TEXT NOT NULL,
                signal_title TEXT NOT NULL,
                signal_description TEXT,
                signal_date DATE,
                signal_strength INTEGER CHECK(signal_strength BETWEEN 1 AND 5),
                firemind_relevance TEXT,
                suggested_use_case TEXT,
                is_verified INTEGER DEFAULT 0,
                confidence TEXT,
                source_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(company_id)
                    REFERENCES companies(company_id)
                    ON DELETE CASCADE,

                FOREIGN KEY(source_id)
                    REFERENCES sources(source_id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS people (
                person_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                full_name TEXT,   -- nullable: NULL means the role is kept but the name is not stored
                job_title TEXT,
                department TEXT,
                persona_type TEXT,
                seniority TEXT,
                linkedin_url TEXT,
                email TEXT,
                location TEXT,
                relevance_reason TEXT,
                priority INTEGER CHECK(priority BETWEEN 1 AND 5),
                source_id INTEGER,
                last_verified_at TIMESTAMP,

                FOREIGN KEY(company_id)
                    REFERENCES companies(company_id)
                    ON DELETE CASCADE,

                FOREIGN KEY(source_id)
                    REFERENCES sources(source_id)
                    ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS account_scores (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                scale_score REAL DEFAULT 0,
                technology_score REAL DEFAULT 0,
                operational_pain_score REAL DEFAULT 0,
                use_case_fit_score REAL DEFAULT 0,
                timing_score REAL DEFAULT 0,
                total_score REAL DEFAULT 0,
                confidence TEXT,
                tier TEXT,
                recommended_use_case TEXT,
                why_now TEXT,
                value_hypothesis TEXT,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(company_id)
                    REFERENCES companies(company_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS outreach (
                outreach_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                person_id INTEGER,
                channel TEXT,
                message_version TEXT,
                subject_line TEXT,
                message_body TEXT,
                status TEXT,
                sent_at TIMESTAMP,
                replied_at TIMESTAMP,
                response_type TEXT,
                meeting_booked INTEGER DEFAULT 0,
                notes TEXT,

                FOREIGN KEY(company_id)
                    REFERENCES companies(company_id)
                    ON DELETE CASCADE,

                FOREIGN KEY(person_id)
                    REFERENCES people(person_id)
                    ON DELETE SET NULL
            );
            """
        )
        self.commit()


def get_connection():
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL UNIQUE,
        sector TEXT NOT NULL,
        subsector TEXT,
        hq_country TEXT,
        employee_count INTEGER,
        revenue_gbp REAL,
        website TEXT,
        linkedin_url TEXT,
        public_private TEXT,
        cloud_environment TEXT,
        it_complexity_notes TEXT,
        fsi_priority_segment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sources (
        source_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT NOT NULL,
        source_title TEXT,
        url TEXT NOT NULL,
        publisher TEXT,
        published_date DATE,
        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        snippet TEXT,
        reliability TEXT
    );

    CREATE TABLE IF NOT EXISTS signals (
        signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        signal_type TEXT NOT NULL,
        signal_title TEXT NOT NULL,
        signal_description TEXT,
        signal_date DATE,
        signal_strength INTEGER CHECK(signal_strength BETWEEN 1 AND 5),
        firemind_relevance TEXT,
        suggested_use_case TEXT,
        is_verified INTEGER DEFAULT 0,
        confidence TEXT,
        source_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(company_id)
            REFERENCES companies(company_id)
            ON DELETE CASCADE,

        FOREIGN KEY(source_id)
            REFERENCES sources(source_id)
            ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS people (
        person_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        full_name TEXT,   -- nullable: NULL means the role is kept but the name is not stored
        job_title TEXT,
        department TEXT,
        persona_type TEXT,
        seniority TEXT,
        linkedin_url TEXT,
        email TEXT,
        location TEXT,
        relevance_reason TEXT,
        priority INTEGER CHECK(priority BETWEEN 1 AND 5),
        source_id INTEGER,
        last_verified_at TIMESTAMP,

        FOREIGN KEY(company_id)
            REFERENCES companies(company_id)
            ON DELETE CASCADE,

        FOREIGN KEY(source_id)
            REFERENCES sources(source_id)
            ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS account_scores (
        score_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        scale_score REAL DEFAULT 0,
        technology_score REAL DEFAULT 0,
        operational_pain_score REAL DEFAULT 0,
        use_case_fit_score REAL DEFAULT 0,
        timing_score REAL DEFAULT 0,
        total_score REAL DEFAULT 0,
        confidence TEXT,
        tier TEXT,
        recommended_use_case TEXT,
        why_now TEXT,
        value_hypothesis TEXT,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(company_id)
            REFERENCES companies(company_id)
            ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS outreach (
        outreach_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        person_id INTEGER,
        channel TEXT,
        message_version TEXT,
        subject_line TEXT,
        message_body TEXT,
        status TEXT,
        sent_at TIMESTAMP,
        replied_at TIMESTAMP,
        response_type TEXT,
        meeting_booked INTEGER DEFAULT 0,
        notes TEXT,

        FOREIGN KEY(company_id)
            REFERENCES companies(company_id)
            ON DELETE CASCADE,

        FOREIGN KEY(person_id)
            REFERENCES people(person_id)
            ON DELETE SET NULL
    );
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database created successfully.")

# ---------------------------------------------------------------------------
# Read helpers used by the scoring pipeline
# ---------------------------------------------------------------------------

def get_company(company_name):
    """Fetch one company row by name, or None."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM companies WHERE company_name = ?",
        (company_name,)
    )

    company = cursor.fetchone()
    conn.close()

    return company


def get_signals(company_id):
    """
    Fetch all signals for a company, joined to source reliability.
    Signal dates are parsed to date objects so scoring can age them.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, src.reliability AS source_reliability
        FROM signals s
        LEFT JOIN sources src ON s.source_id = src.source_id
        WHERE s.company_id = ?
    """, (company_id,))

    rows = cursor.fetchall()
    conn.close()

    signals = []

    for row in rows:
        signal = dict(row)

        if signal["signal_date"]:
            signal["signal_date"] = datetime.strptime(
                signal["signal_date"], "%Y-%m-%d"
            ).date()

        signals.append(signal)

    return signals
