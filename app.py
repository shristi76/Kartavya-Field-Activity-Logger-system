
from pathlib import Path
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file,
)

from PIL import Image, UnidentifiedImageError
from werkzeug.utils import secure_filename

from config import BASE_DIR, PHOTO_DIR

from services.database import (
    initialize_database,
    save_log,
    get_recent_logs,
    get_logs_between,
    get_log_by_id,
    update_log,
    delete_log,
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


def safe_file_path(directory, filename):
    """Resolve a filename inside a specific directory."""
    return directory / Path(filename).name


# ============================================================
# Frontend
# ============================================================

@app.get("/")
def home():
    return render_template("index.html")


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
def get_activities():
    try:
        limit = request.args.get("limit", default=20, type=int)
        limit = min(max(limit or 20, 1), 100)

        logs = get_recent_logs(limit)

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
def get_activity(log_id):
    try:
        log = get_log_by_id(log_id)

        if not log:
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
def create_activity():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request")

    speaker_id = clean_text(data, "speaker_id")
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
    worker_name = clean_text(data, "worker_name")
    organization = clean_text(data, "organization")
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
        )

        saved_log = get_log_by_id(log_id)

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
def edit_activity(log_id):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid JSON request")

    speaker_id = clean_text(data, "speaker_id")
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
                "worker_name": clean_text(
                    data, "worker_name"
                ),
                "organization": clean_text(
                    data, "organization"
                ),
                "district": clean_text(
                    data, "district"
                ),
            },
        )

        if not updated:
            return json_error("Activity not found", 404)

        updated_log = get_log_by_id(log_id)

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
def remove_activity(log_id):
    try:
        deleted = delete_log(log_id)

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
def create_report():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return json_error("Invalid request")

    start_date = clean_text(data, "start_date")
    end_date = clean_text(data, "end_date")
    speaker_id = clean_text(data, "speaker_id")

    if not start_date or not end_date:
        return json_error("Start date and end date are required")

    try:
        # Validate the expected date format.
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start > end:
            return json_error("Start date cannot be after end date")

        logs = get_logs_between(
            start_date,
            end_date,
            speaker_id or None,
        )

        if not logs:
            return json_error("No logs found for this period", 404)

        pdf_path = generate_pdf(
            logs=logs,
            start_date=start_date,
            end_date=end_date,
            speaker_id=speaker_id or None,
        )

        excel_path = generate_excel(
            logs=logs,
            start_date=start_date,
            end_date=end_date,
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
def download_pdf(filename):
    from config import REPORT_DIR as CONFIG_REPORT_DIR

    file_path = safe_file_path(CONFIG_REPORT_DIR, filename)

    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
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
def download_excel(filename):
    from config import EXPORT_DIR

    file_path = safe_file_path(EXPORT_DIR, filename)

    if (
        not file_path.is_file()
        or file_path.suffix.lower() not in {".xlsx", ".xls"}
    ):
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
def play_audio(filename):
    audio_path = safe_file_path(VOICE_DIR, filename)

    if not audio_path.is_file():
        return json_error("Recording not found", 404)

    return send_file(
        audio_path,
        as_attachment=False,
        download_name=audio_path.name,
    )


# ============================================================
# Process Browser Audio
# ============================================================

@app.post("/api/process-audio")
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
def mobile_report():
    try:
        app.logger.info("Mobile report request received")

        if "audio" not in request.files:
            return json_error("No audio file received")

        audio_file = request.files["audio"]

        if not audio_file.filename:
            return json_error("Empty audio file")

        speaker_id = (
            request.form.get("speaker_id") or "mobile_worker"
        ).strip()

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
    )
