# PostgreSQL and accounts setup

1. Install PostgreSQL and create a database/user for this app. For example:

   ```sql
   CREATE USER field_app WITH PASSWORD 'choose-a-unique-password';
   CREATE DATABASE field_activity OWNER field_app;
   ```

2. Copy `.env.example` to `.env`, then set `DATABASE_URL`, a long random `SECRET_KEY`, `ADMIN_WORKER_ID`, a four digit numeric `ADMIN_PASSWORD`, and the existing Gemini settings. Set `COOKIE_SECURE=true` when serving over HTTPS.

3. Install Python packages from `requirements.txt`, then start the Flask server. Database tables and the configured first administrator account are created at app startup. Additional admins must be promoted directly by an administrator with database access; public registration always creates worker accounts.

## Data migration

The former SQLite `field_logs` data is not imported automatically. Those records do not identify a registered account, so assigning them to a worker would expose or attribute records incorrectly. Back up the SQLite file and explicitly map each legacy worker ID to a registered account before importing. PostgreSQL starts with the new account-owned schema.

## Access rules

- Worker accounts can list, view, update, and export only reports owned by their account.
- Administrators can list, view, update, export, and delete reports across accounts.
- Creating accounts publicly never grants administrator privileges.
- Web and mobile sign-in use signed bearer tokens that expire after eight hours. The web app keeps its token in per-tab session storage; mobile keeps it in device storage until sign-out/replacement.
