from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from config import DATABASE_URL


def get_db_connection():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def initialize_database():
    with get_db_connection() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                worker_id TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                organization TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'worker' CHECK (role IN ('worker', 'admin')),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_worker_id_lower ON users (lower(worker_id))")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS field_logs (
                id BIGSERIAL PRIMARY KEY,
                created_at TEXT NOT NULL,
                speaker_id TEXT NOT NULL,
                audio_file TEXT,
                hindi_text TEXT NOT NULL,
                translated_text TEXT,
                activity TEXT,
                beneficiaries TEXT,
                location TEXT,
                worker_name TEXT,
                organization TEXT,
                district TEXT,
                photo_file TEXT,
                user_id BIGINT REFERENCES users(id) ON DELETE CASCADE
            )"""
        )
        connection.execute("ALTER TABLE field_logs ADD COLUMN IF NOT EXISTS photo_file TEXT")
        connection.execute("ALTER TABLE field_logs ADD COLUMN IF NOT EXISTS worker_name TEXT")
        connection.execute("ALTER TABLE field_logs ADD COLUMN IF NOT EXISTS organization TEXT")
        connection.execute("ALTER TABLE field_logs ADD COLUMN IF NOT EXISTS district TEXT")
        connection.execute("ALTER TABLE field_logs ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id) ON DELETE CASCADE")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_field_logs_created_at ON field_logs(created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_field_logs_speaker ON field_logs(speaker_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_field_logs_user ON field_logs(user_id)")


def get_user_by_worker_id(worker_id):
    with get_db_connection() as connection:
        return connection.execute("SELECT * FROM users WHERE lower(worker_id) = lower(%s)", (worker_id,)).fetchone()


def get_user_by_id(user_id):
    with get_db_connection() as connection:
        return connection.execute("SELECT id, name, worker_id, organization, role FROM users WHERE id = %s", (user_id,)).fetchone()


def get_worker_users():
    with get_db_connection() as connection:
        return connection.execute("SELECT id, name, worker_id, organization FROM users WHERE role = 'worker' ORDER BY lower(name), lower(worker_id)").fetchall()


def create_user(name, worker_id, password_hash, organization, role="worker"):
    with get_db_connection() as connection:
        return connection.execute(
            "INSERT INTO users (name, worker_id, password_hash, organization, role) VALUES (%s, %s, %s, %s, %s) RETURNING id, name, worker_id, organization, role",
            (name, worker_id, password_hash, organization, role),
        ).fetchone()


def save_log(speaker_id, audio_file, hindi_text, translated_text, activity, beneficiaries, location, photo_file, worker_name, organization, district, user_id):
    with get_db_connection() as connection:
        row = connection.execute(
            """INSERT INTO field_logs (created_at, speaker_id, audio_file, hindi_text, translated_text, activity,
               beneficiaries, location, worker_name, organization, district, photo_file, user_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), speaker_id, audio_file, hindi_text, translated_text,
             activity, beneficiaries, location, worker_name, organization, district, photo_file, user_id),
        ).fetchone()
        return row["id"]


_LOG_COLUMNS = "id, created_at, speaker_id, audio_file, hindi_text, translated_text, activity, beneficiaries, location, worker_name, organization, district, photo_file, user_id"


def get_recent_logs(limit=20, user_id=None, is_admin=False):
    with get_db_connection() as connection:
        if is_admin:
            if limit is None:
                return connection.execute(f"SELECT {_LOG_COLUMNS} FROM field_logs ORDER BY id DESC").fetchall()
            return connection.execute(f"SELECT {_LOG_COLUMNS} FROM field_logs ORDER BY id DESC LIMIT %s", (limit,)).fetchall()
        return connection.execute(f"SELECT {_LOG_COLUMNS} FROM field_logs WHERE user_id = %s ORDER BY id DESC LIMIT %s", (user_id, limit)).fetchall()


def get_logs_between(start_date, end_date, speaker_id=None, user_id=None, is_admin=False):
    query = "SELECT * FROM field_logs WHERE to_date(created_at, 'YYYY-MM-DD HH24:MI:SS')::date BETWEEN %s AND %s"
    params = [start_date, end_date]
    if speaker_id:
        query += " AND speaker_id = %s"
        params.append(speaker_id)
    if not is_admin:
        query += " AND user_id = %s"
        params.append(user_id)
    query += " ORDER BY to_date(created_at, 'YYYY-MM-DD HH24:MI:SS') ASC"
    with get_db_connection() as connection:
        return connection.execute(query, params).fetchall()


def get_log_by_id(log_id, user_id=None, is_admin=False):
    query = "SELECT * FROM field_logs WHERE id = %s"
    params = [log_id]
    if not is_admin:
        query += " AND user_id = %s"
        params.append(user_id)
    with get_db_connection() as connection:
        return connection.execute(query, params).fetchone()


def get_photo_owner(photo_file):
    with get_db_connection() as connection:
        return connection.execute(
            """SELECT user_id FROM field_logs
               WHERE photo_file = %s OR photo_file LIKE %s
                  OR photo_file LIKE %s OR photo_file LIKE %s LIMIT 1""",
            (photo_file, f"{photo_file},%", f"%,{photo_file},%", f"%,{photo_file}"),
        ).fetchone()


def update_log(log_id, data, user_id=None, is_admin=False):
    query = """UPDATE field_logs SET speaker_id=%s, hindi_text=%s, translated_text=%s, activity=%s,
        beneficiaries=%s, location=%s, worker_name=%s, organization=%s, district=%s WHERE id=%s"""
    params = [data.get("speaker_id"), data.get("hindi_text"), data.get("translated_text", ""), data.get("activity", ""),
              data.get("beneficiaries", ""), data.get("location", ""), data.get("worker_name", ""),
              data.get("organization", ""), data.get("district", ""), log_id]
    if not is_admin:
        query += " AND user_id = %s"
        params.append(user_id)
    with get_db_connection() as connection:
        return connection.execute(query, params).rowcount > 0


def delete_log(log_id, user_id=None, is_admin=False):
    query = "DELETE FROM field_logs WHERE id = %s"
    params = [log_id]
    if not is_admin:
        query += " AND user_id = %s"
        params.append(user_id)
    with get_db_connection() as connection:
        return connection.execute(query, params).rowcount > 0
