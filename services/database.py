import sqlite3

from config import DATABASE_FILE


def get_db_connection():
    """
    Create a connection to the SQLite database.
    """

    connection = sqlite3.connect(DATABASE_FILE)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """
    Create the field_logs table if it doesn't exist.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS field_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_at TEXT NOT NULL,

            speaker_id TEXT NOT NULL,

            audio_file TEXT,

            hindi_text TEXT NOT NULL,

            translated_text TEXT,

            activity TEXT,

            beneficiaries TEXT,

            location TEXT,

            photo_file TEXT
        )
        """
    )

    existing_columns = {
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(field_logs)"
        ).fetchall()
    }

    if "photo_file" not in existing_columns:
        cursor.execute(
            "ALTER TABLE field_logs ADD COLUMN photo_file TEXT"
        )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_field_logs_created_at
        ON field_logs(created_at)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_field_logs_speaker
        ON field_logs(speaker_id)
        """
    )

    connection.commit()

    connection.close()


def save_log(
    speaker_id,
    audio_file,
    hindi_text,
    translated_text,
    activity,
    beneficiaries,
    location,
    photo_file
):
    """
    Save one field activity log.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO field_logs (
            created_at,
            speaker_id,
            audio_file,
            hindi_text,
            translated_text,
            activity,
            beneficiaries,
            location,
            photo_file
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            __import__("datetime")
            .datetime
            .now()
            .strftime("%Y-%m-%d %H:%M:%S"),

            speaker_id,

            audio_file,

            hindi_text,

            translated_text,

            activity,

            beneficiaries,

            location,

            photo_file,
        )
    )

    connection.commit()

    log_id = cursor.lastrowid

    connection.close()

    return log_id


def get_recent_logs(limit=20):
    """
    Return recent field activity logs.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            created_at,
            speaker_id,
            audio_file,
            hindi_text,
            translated_text,
            activity,
            beneficiaries,
            location,
            photo_file
        FROM field_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    logs = cursor.fetchall()

    connection.close()

    return logs


def get_logs_between(
    start_date,
    end_date,
    speaker_id=None
):
    """
    Get logs between two dates.

    Optional speaker_id can be supplied.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    if speaker_id:

        cursor.execute(
            """
            SELECT *
            FROM field_logs
            WHERE date(created_at)
            BETWEEN ? AND ?
            AND speaker_id = ?
            ORDER BY datetime(created_at) ASC
            """,
            (
                start_date,
                end_date,
                speaker_id
            )
        )

    else:

        cursor.execute(
            """
            SELECT *
            FROM field_logs
            WHERE date(created_at)
            BETWEEN ? AND ?
            ORDER BY datetime(created_at) ASC
            """,
            (
                start_date,
                end_date
            )
        )

    logs = cursor.fetchall()

    connection.close()

    return logs


def get_log_by_id(log_id):
    """
    Get one log by ID.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM field_logs
        WHERE id = ?
        """,
        (log_id,)
    )

    log = cursor.fetchone()

    connection.close()

    return log


def delete_log(log_id):
    """
    Delete a field activity log.
    """

    connection = get_db_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM field_logs
        WHERE id = ?
        """,
        (log_id,)
    )

    connection.commit()

    deleted = cursor.rowcount > 0

    connection.close()

    return deleted