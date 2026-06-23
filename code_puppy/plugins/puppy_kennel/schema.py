"""SQLite schema for the puppy_kennel.

Three core tables mirror MemKennel's mental model:

* ``wings``   — top-level partitions (typically a repo / project / agent)
* ``rooms``   — topical sub-partitions within a wing (one per session, usually)
* ``drawers`` — verbatim content chunks (a message, a response, etc.)

An FTS5 virtual table indexes drawer content for BM25 keyword retrieval.
Triggers keep the FTS table in sync with the base table automatically.
"""

from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS wings (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    created_at   TEXT NOT NULL,
    metadata     TEXT
);

CREATE TABLE IF NOT EXISTS rooms (
    id           INTEGER PRIMARY KEY,
    wing_id      INTEGER NOT NULL REFERENCES wings(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    metadata     TEXT,
    UNIQUE(wing_id, name)
);

CREATE TABLE IF NOT EXISTS drawers (
    id           INTEGER PRIMARY KEY,
    room_id      INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    role         TEXT,
    content      TEXT NOT NULL,
    ts           TEXT NOT NULL,
    session_id   TEXT,
    metadata     TEXT
);

CREATE INDEX IF NOT EXISTS idx_drawers_room    ON drawers(room_id);
CREATE INDEX IF NOT EXISTS idx_drawers_session ON drawers(session_id);
CREATE INDEX IF NOT EXISTS idx_drawers_ts      ON drawers(ts);
CREATE INDEX IF NOT EXISTS idx_rooms_wing      ON rooms(wing_id);

CREATE VIRTUAL TABLE IF NOT EXISTS drawers_fts USING fts5(
    content,
    content='drawers',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- Keep FTS in sync with drawers. Triggers are the SQLite-blessed way.
CREATE TRIGGER IF NOT EXISTS drawers_ai AFTER INSERT ON drawers BEGIN
    INSERT INTO drawers_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER IF NOT EXISTS drawers_ad AFTER DELETE ON drawers BEGIN
    INSERT INTO drawers_fts(drawers_fts, rowid, content)
        VALUES('delete', old.id, old.content);
END;

CREATE TRIGGER IF NOT EXISTS drawers_au AFTER UPDATE ON drawers BEGIN
    INSERT INTO drawers_fts(drawers_fts, rowid, content)
        VALUES('delete', old.id, old.content);
    INSERT INTO drawers_fts(rowid, content) VALUES (new.id, new.content);
END;

CREATE TABLE IF NOT EXISTS decisions (
    id                 TEXT PRIMARY KEY,
    title              TEXT NOT NULL,
    status             TEXT NOT NULL,
    confidence         TEXT NOT NULL,
    summary            TEXT NOT NULL,
    rationale          TEXT NOT NULL,
    created_at         TEXT NOT NULL,
    last_reviewed_at   TEXT NOT NULL,
    supersedes_json    TEXT NOT NULL DEFAULT '[]',
    superseded_by_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS decision_repos (
    decision_id TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    repo_name   TEXT NOT NULL,
    PRIMARY KEY(decision_id, repo_name)
);

CREATE TABLE IF NOT EXISTS decision_evidence_artifacts (
    decision_id TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    artifact_id TEXT NOT NULL,
    PRIMARY KEY(decision_id, artifact_id)
);

CREATE INDEX IF NOT EXISTS idx_decisions_status ON decisions(status);
CREATE INDEX IF NOT EXISTS idx_decisions_reviewed ON decisions(last_reviewed_at);
CREATE INDEX IF NOT EXISTS idx_decision_repos_repo_name ON decision_repos(repo_name);

CREATE TABLE IF NOT EXISTS doctrine_receipts (
    id              INTEGER PRIMARY KEY,
    ts              TEXT NOT NULL,
    decision_id     TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    repo_family     TEXT NOT NULL,
    proposed_action TEXT NOT NULL,
    warning_shown   INTEGER NOT NULL,
    adapted         INTEGER NOT NULL,
    before_summary  TEXT NOT NULL,
    after_summary   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_doctrine_receipts_ts ON doctrine_receipts(ts);
CREATE INDEX IF NOT EXISTS idx_doctrine_receipts_decision_id ON doctrine_receipts(decision_id);
CREATE INDEX IF NOT EXISTS idx_doctrine_receipts_repo_family ON doctrine_receipts(repo_family);
"""

# PRAGMAs applied on every connection. WAL is the headline: one writer +
# unlimited readers, multi-process safe, the whole reason we picked SQLite.
PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",  # WAL durability is fine at NORMAL; faster.
    "PRAGMA foreign_keys=ON",
    "PRAGMA busy_timeout=5000",  # 5s grace for writers waiting on the lock.
)
