
from pathlib import Path
from datetime import datetime, timedelta
import os

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity
from flask_jwt_extended import verify_jwt_in_request
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from functools import wraps

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from config import BASE_DIR, PHOTO_DIR, SECRET_KEY, ADMIN_WORKER_ID, ADMIN_PASSWORD, DATABASE_URL

from services.database import (
    initialize_database,
    save_log,
    get_recent_logs,
    get_logs_between,
    get_log_by_id,
    update_log,
    delete_log,
    get_user_by_worker_id,
    get_user_by_id,
    create_user,
    get_photo_owner,
    get_worker_users,
)

from services.gemini_service import parse_activity_with_gemini

from services.report_service import (
    generate_pdf,
    generate_excel,
)

from services.speech_service import transcribe_audio_file


# ============================================================
# Flask App
# ============================================================

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config.update(SECRET_KEY=SECRET_KEY, JWT_SECRET_KEY=SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=8))
CORS(app, origins=os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [])
JWTManager(app)
password_hasher = PasswordHasher()


# ============================================================
# Configuration
# ============================================================

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}

VOICE_DIR = BASE_DIR / "Voice_Samples"
REPORT_DIR = BASE_DIR / "Generated_Reports"

VOICE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Initialize Database
# ============================================================

initialize_database()


def initialize_admin_account():
    if not ADMIN_WORKER_ID or not ADMIN_PASSWORD:
        app.logger.warning("Admin account is not configured; set ADMIN_WORKER_ID and ADMIN_PASSWORD")
        return
    existing = get_user_by_worker_id(ADMIN_WORKER_ID)
    if existing:
        if existing["role"] != "admin":
            from services.database import get_db_connection
            with get_db_connection() as connection:
                connection.execute("UPDATE users SET role = 'admin' WHERE id = %s", (existing["id"],))
        return
    create_user("Administrator", ADMIN_WORKER_ID, password_hasher.hash(ADMIN_PASSWORD), "Administration", "admin")


initialize_admin_account()


# ============================================================
# Helper Functions
# ============================================================

def json_error(message, status_code=400):
    """Return a consistent JSON error response."""
    return jsonify({
        "success": False,
        "error": message,
    }), status_code


def clean_text(data, field):
    """Return a trimmed string for a request field."""
    return str(data.get(field) or "").strip()


def valid_pin(value):
    return len(value) == 4 and value.isascii() and value.isdigit()


def safe_file_path(directory, filename):
    """Resolve a filename inside a specific directory."""
    return directory / Path(filename).name


def current_user():
    identity = None
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
    except Exception:
        identity = None
    if identity is None:
        return None
    return get_user_by_id(int(identity))


def require_auth(admin=False):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return json_error("Authentication required", 401)
            if admin and user["role"] != "admin":
                return json_error("Administrator access required", 403)
            request.current_user = user
            return function(*args, **kwargs)
        return wrapped
    return decorator


# ============================================================
# Frontend
# ============================================================

@app.get("/")
def home():
    return render_template("index.html")


@app.get("/auth")
def auth_page():
    return render_template("auth.html")


@app.get("/admin")
def admin_page():
    return render_template("admin.html")


@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name, worker_id = clean_text(data, "name"), clean_text(data, "worker_id")
    password, organization = str(data.get("password") or ""), clean_text(data, "organization")
    if not all((name, worker_id, password, organization)):
        return json_error("Name, worker ID, password, and organisation are required")
    if not valid_pin(password):
        return json_error("PIN must be exactly 4 digits")
    try:
        user = create_user(name, worker_id, password_hasher.hash(password), organization)
        return jsonify({"success": True, "data": dict(user), "message": "Registration successful. Please sign in."}), 201
    except Exception as error:
        if "unique" in str(error).lower():
            return json_error("That worker ID is already registered", 409)
        app.logger.exception("Registration error")
        return json_error("Could not register account", 500)


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    user = get_user_by_worker_id(clean_text(data, "worker_id"))
    password = str(data.get("password") or "")
    if not valid_pin(password):
        return json_error("PIN must be exactly 4 digits")
    try:
        if not user:
            return json_error("Invalid worker ID or password", 401)
        password_hasher.verify(user["password_hash"], password)
    except VerifyMismatchError:
        return json_error("Invalid worker ID or password", 401)
    except Exception:
        return json_error("Invalid worker ID or password", 401)
    token = create_access_token(identity=str(user["id"]))
    public_user = {key: user[key] for key in ("id", "name", "worker_id", "organization", "role")}
    return jsonify({"success": True, "data": public_user, "access_token": token})


@app.post("/api/auth/logout")
def logout():
    return jsonify({"success": True})


@app.get("/api/auth/me")
@require_auth()
def auth_me():
    return jsonify({"success": True, "data": dict(request.current_user)})


@app.get("/api/admin/activities")
@require_auth(admin=True)
def admin_activities():
    return jsonify({"success": True, "data": [dict(row) for row in get_recent_logs(None, is_admin=True)]})


@app.get("/api/admin/workers")
@require_auth(admin=True)
def admin_workers():
    return jsonify({"success": True, "data": [dict(row) for row in get_worker_users()]})


@app.post("/api/admin/activities")
@require_auth(admin=True)
def admin_create_activity():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return json_error("Invalid JSON request")
    worker_id = clean_text(data, "speaker_id")
    hindi_text = clean_text(data, "hindi_text")
    if not worker_id or not hindi_text:
        return json_error("Worker ID and Hindi transcription are required")
    worker = get_user_by_worker_id(worker_id)
    if not worker or worker["role"] != "worker":
        return json_error("Select a registered worker account")
    try:
        log_id = save_log(
            speaker_id=worker["worker_id"],
            audio_file=None,
            hindi_text=hindi_text,
            translated_text=clean_text(data, "translated_text"),
            activity=clean_text(data, "activity"),
            beneficiaries=clean_text(data, "beneficiaries"),
            location=clean_text(data, "location"),
            photo_file=None,
            worker_name=worker["name"],
            organization=worker["organization"],
            district=clean_text(data, "district"),
            user_id=worker["id"],
        )
        report = get_log_by_id(log_id, is_admin=True)
        return jsonify({"success": True, "message": "Report created for worker", "data": dict(report)}), 201
    except Exception:
        app.logger.exception("Admin activity creation error")
        return json_error("Could not create report", 500)


# ============================================================
# Health Check
# ============================================================

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "Field Activity API is running",
    })


# ============================================================
# Get Recent Activities
# ============================================================

@app.get("/api/activities")
@require_auth()
def get_activities():
    try:
        user = request.current_user
        if user["role"] == "admin":
            logs = get_recent_logs(None, is_admin=True)
        else:
            limit = min(max(request.args.get("limit", default=20, type=int) or 20, 1), 100)
            logs = get_recent_logs(limit, user_id=user["id"])

        return jsonify({
            "success": True,
            "data": [dict(log) for log in logs],
        })

    except Exception:
        app.logger.exception("Get activities error")
        return json_error("Could not retrieve activities", 500)


# ============================================================
# Get Single Activity
# ============================================================

@app.get("/api/activities/<int:log_id>")
@require_auth()
def get_activity(log_id):
    try:
        user = request.current_user
        log = get_log_by_id(log_id, user_id=user["id"], is_admin=user["role"] == "admin")

        if not log:
            return json_error("Activity not found", 404)

        if request.current_user["role"] != "admin" and log["user_id"] != request.current_user["id"]:
            return json_error("Activity not found", 404)

        return jsonify({
            "success": True,
            "data": dict(log),
        })

    except Exception:
        app.logger.exception("Get activity error")
        return json_error("Could not retrieve activity", 500)


# ============================================================
# Process Hindi Text
# ============================================================

@app.post("/api/process")
@require_auth()
def process_activity():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request")

    hindi_text = clean_text(data, "hindi_text")

    if not hindi_text:
        return json_error("Hindi text is required")

    try:
        result = parse_activity_with_gemini(hindi_text)

        return jsonify({
            "success": True,
            "data": result,
        })

    except Exception:
        app.logger.exception("Text processing error")
        return json_error("Could not process the Hindi text", 500)


# ============================================================
# Save Reviewed Activity
# ============================================================

@app.post("/api/activities")
@require_auth()
def create_activity():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request")

    user = request.current_user
    speaker_id = user["worker_id"]
    hindi_text = clean_text(data, "hindi_text")

    if not speaker_id:
        return json_error("Worker ID is required")

    if not hindi_text:
        return json_error("Hindi text is required")

    # Save reviewed values supplied by the frontend.
    # Do not call Gemini again or overwrite user edits.
    translated_text = clean_text(data, "translated_text")
    activity = clean_text(data, "activity")
    beneficiaries = clean_text(data, "beneficiaries")
    location = clean_text(data, "location")

    # New fields
    worker_name = user["name"]
    organization = user["organization"]
    district = clean_text(data, "district")

    audio_file = clean_text(data, "audio_file") or None
    photo_file = clean_text(data, "photo_file") or None

    try:
        log_id = save_log(
            speaker_id=speaker_id,
            audio_file=audio_file,
            hindi_text=hindi_text,
            translated_text=translated_text,
            activity=activity,
            beneficiaries=beneficiaries,
            location=location,
            photo_file=photo_file,
            worker_name=worker_name,
            organization=organization,
            district=district,
            user_id=user["id"],
        )

        saved_log = get_log_by_id(log_id, user_id=user["id"])

        if not saved_log:
            app.logger.error(
                "Activity %s was saved but could not be retrieved",
                log_id,
            )
            return json_error("Activity saved but could not be retrieved", 500)

        return jsonify({
            "success": True,
            "message": "Reviewed activity saved successfully",
            "data": dict(saved_log),
        }), 201

    except Exception:
        app.logger.exception("Activity save error")
        return json_error("Could not save activity", 500)


# ============================================================
# Edit Activity
# ============================================================

@app.put("/api/activities/<int:log_id>")
@require_auth()
def edit_activity(log_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request")

    user = request.current_user
    speaker_id = clean_text(data, "speaker_id") if user["role"] == "admin" else user["worker_id"]
    hindi_text = clean_text(data, "hindi_text")

    if not speaker_id:
        return json_error("Worker ID is required")

    if not hindi_text:
        return json_error("Hindi text is required")

    try:
        updated = update_log(
            log_id,
            {
                "speaker_id": speaker_id,
                "hindi_text": hindi_text,
                "translated_text": clean_text(
                    data, "translated_text"
                ),
                "activity": clean_text(
                    data, "activity"
                ),
                "beneficiaries": clean_text(
                    data, "beneficiaries"
                ),
                "location": clean_text(
                    data, "location"
                ),

                # New editable fields
                "worker_name": clean_text(data, "worker_name") if user["role"] == "admin" else user["name"],
                "organization": clean_text(data, "organization") if user["role"] == "admin" else user["organization"],
                "district": clean_text(
                    data, "district"
                ),
            },
            user_id=user["id"],
            is_admin=user["role"] == "admin",
        )

        if not updated:
            return json_error("Activity not found", 404)

        updated_log = get_log_by_id(log_id, user_id=user["id"], is_admin=user["role"] == "admin")

        if not updated_log:
            return json_error("Updated activity could not be retrieved", 500)

        return jsonify({
            "success": True,
            "message": "Activity updated successfully",
            "data": dict(updated_log),
        }), 200

    except Exception:
        app.logger.exception("Update activity error")
        return json_error("Could not update activity", 500)


# ============================================================
# Upload Activity Photo
# ============================================================

@app.post("/api/uploads/photo")
@require_auth()
def upload_photo():
    photo = request.files.get("photo")

    if not photo or not photo.filename:
        return json_error("Please select a photo")

    extension = (
        Path(photo.filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        return json_error("Only JPG and PNG photos are supported")

    try:
        photo.stream.seek(0)

        with Image.open(photo.stream) as image:
            image.verify()

        photo.stream.seek(0)

    except (UnidentifiedImageError, OSError):
        return json_error("The selected file is not a valid photo")

    safe_name = secure_filename(photo.filename)

    if not safe_name:
        return json_error("Invalid photo filename")

    # Normalize the extension and avoid trusting the original path.
    filename = (
        f"user_{request.current_user['id']}_"
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_"
        f"{safe_name}"
    )

    output_path = PHOTO_DIR / filename

    try:
        photo.save(output_path)

        return jsonify({
            "success": True,
            "data": {
                "filename": filename,
            },
        }), 201

    except Exception:
        app.logger.exception("Photo upload error")
        return json_error("Could not save photo", 500)


# ============================================================
# Delete Activity
# ============================================================

@app.delete("/api/activities/<int:log_id>")
@require_auth(admin=True)
def remove_activity(log_id):
    try:
        deleted = delete_log(log_id, user_id=request.current_user["id"], is_admin=True)

        if not deleted:
            return json_error("Activity not found", 404)

        return jsonify({
            "success": True,
            "message": "Activity deleted successfully",
        })

    except Exception:
        app.logger.exception("Delete activity error")
        return json_error("Could not delete activity", 500)


# ============================================================
# Generate PDF and Excel Reports
# ============================================================

@app.post("/api/reports")
@require_auth()
def create_report():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid request")

    start_date = clean_text(data, "start_date")
    end_date = clean_text(data, "end_date")
    speaker_id = clean_text(data, "speaker_id")
    log_id = request.args.get("log_id", type=int) or data.get("log_id")

    if not log_id and (not start_date or not end_date):
        return json_error("Start date and end date are required")

    try:
        user = request.current_user
        if log_id:
            selected = get_log_by_id(log_id, user_id=user["id"], is_admin=user["role"] == "admin")
            logs = [selected] if selected else []
            if selected:
                selected_date = str(selected["created_at"])[:10]
                start_date = end_date = selected_date
                speaker_id = selected["speaker_id"]
        else:
            # Validate the expected date format.
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start > end:
                return json_error("Start date cannot be after end date")

            logs = get_logs_between(
                start_date,
                end_date,
                speaker_id or (None if user["role"] == "admin" else user["worker_id"]),
                user_id=user["id"],
                is_admin=user["role"] == "admin",
            )

        if not logs:
            return json_error("No logs found for this period", 404)

        pdf_path = generate_pdf(
            logs=logs,
            start_date=start_date,
            end_date=end_date,
            speaker_id=speaker_id or None,
            owner_id=None if user["role"] == "admin" else user["id"],
            report_tag=f"log_{log_id}" if log_id else None,
        )

        excel_path = generate_excel(
            logs=logs,
            start_date=start_date,
            end_date=end_date,
            owner_id=None if user["role"] == "admin" else user["id"],
            report_tag=f"log_{log_id}" if log_id else None,
        )

        return jsonify({
            "success": True,
            "message": "Reports generated successfully",
            "data": {
                "pdf": pdf_path.name,
                "excel": excel_path.name,
                "generated_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        })

    except ValueError:
        return json_error("Dates must use YYYY-MM-DD format")

    except Exception:
        app.logger.exception("Report generation error")
        return json_error("Could not generate reports", 500)


# ============================================================
# Download PDF
# ============================================================

@app.get("/api/reports/pdf/<filename>")
@require_auth()
def download_pdf(filename):
    from config import REPORT_DIR as CONFIG_REPORT_DIR

    file_path = safe_file_path(CONFIG_REPORT_DIR, filename)

    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
        return json_error("PDF not found", 404)

    user = request.current_user
    if user["role"] != "admin" and f"user_{user['id']}_" not in file_path.name:
        return json_error("PDF not found", 404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_path.name,
    )


# ============================================================
# Download Excel
# ============================================================

@app.get("/api/reports/excel/<filename>")
@require_auth()
def download_excel(filename):
    from config import EXPORT_DIR

    file_path = safe_file_path(EXPORT_DIR, filename)

    if (
        not file_path.is_file()
        or file_path.suffix.lower() not in {".xlsx", ".xls"}
    ):
        return json_error("Excel file not found", 404)

    user = request.current_user
    if user["role"] != "admin" and f"user_{user['id']}_" not in file_path.name:
        return json_error("Excel file not found", 404)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=file_path.name,
    )


# ============================================================
# Play / Download Audio
# ============================================================

@app.get("/api/audio/<filename>")
@require_auth()
def play_audio(filename):
    audio_path = safe_file_path(VOICE_DIR, filename)

    if not audio_path.is_file():
        return json_error("Recording not found", 404)

    user = request.current_user
    if user["role"] != "admin":
        from services.database import get_db_connection
        with get_db_connection() as connection:
            owned = connection.execute("SELECT 1 FROM field_logs WHERE user_id = %s AND audio_file = %s", (user["id"], filename)).fetchone()
        if not owned:
            return json_error("Recording not found", 404)

    return send_file(
        audio_path,
        as_attachment=False,
        download_name=audio_path.name,
    )


@app.get("/api/photos/<filename>")
@require_auth()
def get_photo(filename):
    photo_path = safe_file_path(PHOTO_DIR, filename)
    if not photo_path.is_file():
        return json_error("Photo not found", 404)
    user = request.current_user
    owner = get_photo_owner(filename)
    if user["role"] != "admin" and (not owner or owner["user_id"] != user["id"]):
        return json_error("Photo not found", 404)
    return send_file(photo_path)


# ============================================================
# Process Browser Audio
# ============================================================

@app.post("/api/process-audio")
@require_auth()
def process_audio():
    audio_path = None

    try:
        if "audio" not in request.files:
            return json_error("No audio file received")

        audio_file = request.files["audio"]

        if not audio_file.filename:
            return json_error("Empty audio file")

        filename = (
            f"browser_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            f".webm"
        )

        audio_path = VOICE_DIR / filename
        audio_file.save(audio_path)

        transcription = transcribe_audio_file(audio_path)

        if not transcription:
            return json_error("Could not understand the audio")

        return jsonify({
            "success": True,
            "transcription": transcription,
            "audio_file": filename,
            "recorded_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        })

    except Exception:
        app.logger.exception("Audio processing error")
        return json_error("Could not process the audio", 500)


# ============================================================
# Mobile App - Process Voice Report
# ============================================================

@app.post("/api/report")
@require_auth()
def mobile_report():
    try:
        app.logger.info("Mobile report request received")

        if "audio" not in request.files:
            return json_error("No audio file received")

        audio_file = request.files["audio"]

        if not audio_file.filename:
            return json_error("Empty audio file")

        speaker_id = request.current_user["worker_id"]

        safe_speaker_id = secure_filename(speaker_id)

        if not safe_speaker_id:
            safe_speaker_id = "mobile_worker"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{safe_speaker_id}_{timestamp}.m4a"

        audio_path = VOICE_DIR / filename
        audio_file.save(audio_path)

        transcription = transcribe_audio_file(audio_path)

        if not transcription:
            return json_error("Could not understand the audio")

        parsed = parse_activity_with_gemini(transcription)

        # The user reviews and edits the report before saving.
        # Nothing is saved to the activity database here.
        return jsonify({
            "success": True,
            "report": parsed,
            "transcription": transcription,
            "audio_file": filename,
            "activity_id": None,
        }), 200

    except Exception:
        app.logger.exception("Mobile report error")
        return json_error("Could not process the mobile report", 500)


# ============================================================
# Start Server
# ============================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,
    )
