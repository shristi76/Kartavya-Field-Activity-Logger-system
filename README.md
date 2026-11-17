# Kartavya — Field Activity Logger

> A secure field-reporting platform for capturing community work in Hindi, Hinglish, or English and turning it into structured, shareable reports.

[![Backend](https://img.shields.io/badge/backend-Flask-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Mobile](https://img.shields.io/badge/mobile-Expo%20%2B%20React%20Native-000020?logo=expo&logoColor=white)](https://expo.dev/)
[![Language](https://img.shields.io/badge/AI%20input-Hindi%20%7C%20Hinglish%20%7C%20English-orange)](https://ai.google.dev/)

Kartavya helps field workers record visits and community activities without manually writing long reports. A worker can record a voice note, review the transcription and AI-generated fields, attach a photo, and save the final activity. Administrators get a cross-worker dashboard with secure access to reports and exports.

## Highlights

- **Voice-first reporting:** upload or record audio and transcribe field notes.
- **Structured extraction:** use Gemini to translate Hindi/Hinglish and extract report fields.
- **Human review:** AI output is editable before anything is saved.
- **Web and mobile clients:** use the Flask web interface or the Expo app.
- **Evidence capture:** store activity audio and photos with the report.
- **Reports that are ready to share:** generate styled PDF and Excel exports.
- **Role-based access:** workers see their own records; administrators manage all records.
- **Secure authentication:** four-digit worker PINs are hashed with Argon2 and sessions use expiring JWT bearer tokens.
- **PostgreSQL-backed data:** account ownership and report access are enforced at the database/API layer.

## How it works

```text
Record or upload audio
        ↓
Speech-to-text transcription
        ↓
Gemini translation and field extraction
        ↓
Worker reviews and edits the report
        ↓
Save activity + optional photo
        ↓
Generate PDF or Excel export
```

The AI step does **not** save an activity by itself. Users review the generated report and explicitly submit it, which helps prevent transcription or extraction errors from becoming official records.

## Report fields

Reports can include the worker, date, location, village, block, district, organization, activity, people and households visited, beneficiaries assisted, identified issues, assistance and actions taken, referrals, services accessed, follow-up details, outcomes, the original translated statement, and additional notes.

## Repository structure

```text
.
├── app.py                    # Flask application and API routes
├── config.py                 # Environment-driven application configuration
├── services/
│   ├── database.py           # PostgreSQL access and account/report queries
│   ├── gemini_service.py     # Translation and structured report extraction
│   ├── report_service.py     # PDF and Excel generation
│   └── speech_service.py     # Audio preparation and transcription
├── templates/                # Web pages
├── static/                   # Web CSS and JavaScript
├── mobile/                   # Expo / React Native application
├── data/                     # Runtime media and generated files
├── requirements.txt          # Python dependencies
└── POSTGRES_SETUP.md         # PostgreSQL and migration notes
```

## Prerequisites

- Python 3.10 or newer
- PostgreSQL 14 or newer
- Node.js 18 or newer and npm
- A Google Gemini API key and a model name
- FFmpeg available on `PATH` for audio formats that require conversion

## Backend setup

### 1. Clone the repository

```bash
git clone https://github.com/shristi76/Kartavya-Field-Activity-Logger-system.git
cd Kartavya-Field-Activity-Logger-system
```

### 2. Create the database

```sql
CREATE USER field_app WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE field_activity OWNER field_app;
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` before starting the server:

```dotenv
DATABASE_URL=postgresql://field_app:choose-a-strong-password@localhost:5432/field_activity
SECRET_KEY=replace_with_a_long_random_secret
ADMIN_WORKER_ID=admin
ADMIN_PASSWORD=change_this_four_digit_pin
COOKIE_SECURE=false
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
```

Use `COOKIE_SECURE=true` when serving the application over HTTPS. Never commit `.env`, real credentials, API keys, or production media to source control.

### 4. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install FFmpeg separately if it is not already available:

```bash
ffmpeg -version
```

### 5. Start the API and web app

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000). The API health check is available at [http://localhost:5000/api/health](http://localhost:5000/api/health).

Database tables and the configured initial administrator account are created at startup. Public registration creates worker accounts; it does not grant administrator privileges.

## Mobile app setup

The mobile app is in `mobile/` and uses Expo Router.

```bash
cd mobile
npm install
npx expo start
```

Then choose an Android emulator, iOS simulator, Expo Go, or web. Before running on a physical device, update `API_BASE_URL` in `mobile/src/services/api.ts` to the backend host reachable from that device. `localhost` inside a phone or emulator refers to the device itself, not the development computer.

Available scripts:

```bash
npm run start    # Start Expo
npm run android  # Start with Android
npm run ios      # Start with iOS
npm run web      # Start the web target
npm run lint     # Run Expo linting
```

## Main API routes

All protected routes require an `Authorization: Bearer <token>` header after login.

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Register a worker account |
| `POST` | `/api/auth/login` | Sign in and receive an access token |
| `GET` | `/api/auth/me` | Get the current account |
| `POST` | `/api/process-audio` | Transcribe browser audio |
| `POST` | `/api/report` | Transcribe mobile audio and generate a draft report |
| `POST` | `/api/process` | Extract a structured report from reviewed text |
| `POST` | `/api/activities` | Save a reviewed activity |
| `GET` | `/api/activities` | List activities owned by the current worker |
| `PUT` | `/api/activities/<id>` | Update an activity |
| `POST` | `/api/uploads/photo` | Upload activity evidence |
| `POST` | `/api/reports` | Generate PDF and Excel exports |
| `GET` | `/api/health` | Check API availability |

Administrator-only routes provide worker management, cross-account activity views, administrator-created activities, and deletion of activities.

## Access model

| Account type | Permissions |
| --- | --- |
| Worker | Create, view, update, and export only their own activities |
| Administrator | View, create, update, export, and delete activities across workers |

Authentication tokens expire after eight hours. Worker PINs are stored as Argon2 hashes rather than plaintext values.

## PostgreSQL and migration notes

See [`POSTGRES_SETUP.md`](POSTGRES_SETUP.md) for database setup, access rules, and the SQLite migration guidance. Legacy SQLite records are not imported automatically because they are not reliably associated with registered accounts; map ownership explicitly before importing any historical data.

## Screenshots

### System overview

<img src="https://github.com/user-attachments/assets/0859c412-f7f3-4556-9131-536e6294bb70" alt="Kartavya field activity application sequence diagram" width="900">

### Mobile recording flow

<img src="https://github.com/user-attachments/assets/5d3d895e-48f0-413a-b3a9-8582ab158fc9" alt="Kartavya mobile activity recording screen" width="300">

### Dashboard

<img src="https://github.com/user-attachments/assets/74346a24-6a46-42b2-ac42-b9b07ecd1be1" alt="Kartavya activity dashboard" width="500">

### Generated output

<img src="https://github.com/user-attachments/assets/f107b52f-5066-4857-a1f3-35ed89d41472" alt="Kartavya generated report output" width="500">

## Troubleshooting

- **Database connection fails:** verify PostgreSQL is running and `DATABASE_URL` matches the database, user, password, and port.
- **Audio conversion fails:** install FFmpeg and confirm `ffmpeg -version` works in the same terminal used to start Flask.
- **Gemini processing fails:** check `GEMINI_API_KEY`, `GEMINI_MODEL`, network access, and API quota.
- **Mobile requests fail on a physical device:** use the computer's LAN IP in `API_BASE_URL`, keep both devices on the same network, and allow inbound connections to port `5000`.
- **PDF text is missing or malformed:** ensure the bundled Devanagari fonts and the `uharfbuzz` dependency are present.

## Security checklist

- Replace every example secret and PIN before deployment.
- Keep `.env`, generated reports, uploaded photos, and recordings out of Git.
- Run behind HTTPS in production and set `COOKIE_SECURE=true`.
- Restrict PostgreSQL network access and use a least-privilege database account.
- Rotate the Gemini key and application secret if they are ever exposed.
- Back up PostgreSQL and the runtime media directories independently.

## License

This project includes the [`mobile/LICENSE`](mobile/LICENSE) file. Review the repository's licensing terms before redistributing or deploying the project.

