"""Import legacy SQLite logs after mapping each speaker_id to a PostgreSQL worker account.

Usage: python scripts/migrate_sqlite_to_postgres.py path/to/field_logs.db
"""
import argparse
import sqlite3

from services.database import get_db_connection, get_user_by_worker_id, initialize_database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_file")
    args = parser.parse_args()
    initialize_database()
    source = sqlite3.connect(args.sqlite_file)
    source.row_factory = sqlite3.Row
    rows = source.execute("SELECT * FROM field_logs ORDER BY id").fetchall()
    mapping = {}
    for row in rows:
        worker_id = row["speaker_id"]
        if worker_id not in mapping:
            user = get_user_by_worker_id(worker_id)
            while not user:
                print(f"No PostgreSQL account found for legacy worker ID: {worker_id!r}")
                mapping[worker_id] = input("Enter the matching PostgreSQL worker ID: ").strip()
                user = get_user_by_worker_id(mapping[worker_id])
            mapping[worker_id] = user["id"]
    columns = ("created_at", "speaker_id", "audio_file", "hindi_text", "translated_text", "activity", "beneficiaries", "location", "worker_name", "organization", "district", "photo_file", "user_id")
    with get_db_connection() as target:
        for row in rows:
            values = [row[key] if key in row.keys() else None for key in columns[:-1]]
            values.append(mapping[row["speaker_id"]])
            target.execute(
                f"INSERT INTO field_logs ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})",
                values,
            )
    source.close()
    print(f"Imported {len(rows)} records.")


if __name__ == "__main__":
    main()
