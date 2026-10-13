
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
        limit = min(max(limit, 1), 100)

        logs = get_recent_logs(limit)

        return jsonify({
            "success": True,
            "data": [dict(log) for log in logs],
        })

    except Exception as error:
        print("Get activities error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Get Single Activity
# ============================================================

@app.get("/api/activities/<int:log_id>")
def get_activity(log_id):
    try:
        log = get_log_by_id(log_id)

        if not log:
            return jsonify({
                "success": False,
                "error": "Activity not found",
            }), 404

        return jsonify({
            "success": True,
            "data": dict(log),
        })

    except Exception as error:
        print("Get activity error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Process Hindi Text
# ============================================================

@app.post("/api/process")
def process_activity():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid JSON request",
        }), 400

    hindi_text = str(data.get("hindi_text") or "").strip()

    if not hindi_text:
        return jsonify({
            "success": False,
            "error": "Hindi text is required",
        }), 400

    try:
        result = parse_activity_with_gemini(hindi_text)

        return jsonify({
            "success": True,
            "data": result,
        })

    except Exception as error:
        print("Text processing error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Save Reviewed Activity
# ============================================================

@app.post("/api/activities")
def create_activity():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid JSON request",
        }), 400

    speaker_id = str(data.get("speaker_id") or "").strip()
    hindi_text = str(data.get("hindi_text") or "").strip()

    if not speaker_id:
        return jsonify({
            "success": False,
            "error": "Speaker ID is required",
        }), 400

    if not hindi_text:
        return jsonify({
            "success": False,
            "error": "Hindi text is required",
        }), 400

    # Save the reviewed values supplied by the mobile app.
    # Do not call Gemini again or replace user edits.
    translated_text = str(data.get("translated_text") or "").strip()
    activity = str(data.get("activity") or "").strip()
    beneficiaries = str(data.get("beneficiaries") or "").strip()
    location = str(data.get("location") or "").strip()

    audio_file = data.get("audio_file") or None
    photo_file = data.get("photo_file") or None

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
        )

        saved_log = get_log_by_id(log_id)

        return jsonify({
            "success": True,
            "message": "Reviewed activity saved successfully",
            "data": dict(saved_log),
        }), 201

    except Exception as error:
        print("Activity save error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Edit Activity
# ============================================================

@app.put("/api/activities/<int:log_id>")
def edit_activity(log_id):
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid JSON request",
        }), 400

    speaker_id = str(data.get("speaker_id") or "").strip()
    hindi_text = str(data.get("hindi_text") or "").strip()

    if not speaker_id:
        return jsonify({
            "success": False,
            "error": "Speaker ID is required",
        }), 400

    if not hindi_text:
        return jsonify({
            "success": False,
            "error": "Hindi text is required",
        }), 400

    try:
        updated = update_log(
            log_id,
            {
                "speaker_id": speaker_id,
                "hindi_text": hindi_text,
                "translated_text": str(
                    data.get("translated_text") or ""
                ).strip(),
                "activity": str(
                    data.get("activity") or ""
                ).strip(),
                "beneficiaries": str(
                    data.get("beneficiaries") or ""
                ).strip(),
                "location": str(
                    data.get("location") or ""
                ).strip(),
            },
        )

        if not updated:
            return jsonify({
                "success": False,
                "error": "Activity not found",
            }), 404

        updated_log = get_log_by_id(log_id)

        return jsonify({
            "success": True,
            "message": "Activity updated successfully",
            "data": dict(updated_log),
        }), 200

    except Exception as error:
        print("Update activity error:", error)

        return jsonify({
            "success": False,
            "error": "Could not update activity",
        }), 500


# ============================================================
# Upload Activity Photo
# ============================================================

@app.post("/api/uploads/photo")
def upload_photo():
    photo = request.files.get("photo")

    if not photo or not photo.filename:
        return jsonify({
            "success": False,
            "error": "Please select a photo",
        }), 400

    extension = (
        Path(photo.filename)
        .suffix
        .lower()
        .lstrip(".")
    )

    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "Only JPG and PNG photos are supported",
        }), 400

    try:
        photo.stream.seek(0)

        with Image.open(photo.stream) as image:
            image.verify()

        photo.stream.seek(0)

    except (UnidentifiedImageError, OSError):
        return jsonify({
            "success": False,
            "error": "The selected file is not a valid photo",
        }), 400

    safe_name = secure_filename(photo.filename)

    if not safe_name:
        return jsonify({
            "success": False,
            "error": "Invalid photo filename",
        }), 400

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

    except Exception as error:
        print("Photo upload error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Delete Activity
# ============================================================

@app.delete("/api/activities/<int:log_id>")
def remove_activity(log_id):
    try:
        deleted = delete_log(log_id)

        if not deleted:
            return jsonify({
                "success": False,
                "error": "Activity not found",
            }), 404

        return jsonify({
            "success": True,
            "message": "Activity deleted successfully",
        })

    except Exception as error:
        print("Delete activity error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Generate PDF and Excel Reports
# ============================================================

@app.post("/api/reports")
def create_report():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "Invalid request",
        }), 400

    start_date = str(data.get("start_date") or "").strip()
    end_date = str(data.get("end_date") or "").strip()
    speaker_id = str(data.get("speaker_id") or "").strip()

    if not start_date or not end_date:
        return jsonify({
            "success": False,
            "error": "Start date and end date are required",
        }), 400

    try:
        logs = get_logs_between(
            start_date,
            end_date,
            speaker_id or None,
        )

        if not logs:
            return jsonify({
                "success": False,
                "error": "No logs found for this period",
            }), 404

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

    except Exception as error:
        print("Report generation error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Download PDF
# ============================================================

@app.get("/api/reports/pdf/<filename>")
def download_pdf(filename):
    from config import REPORT_DIR

    file_path = REPORT_DIR / Path(filename).name

    if not file_path.is_file():
        return jsonify({
            "success": False,
            "error": "PDF not found",
        }), 404

    return send_file(file_path, as_attachment=True)


# ============================================================
# Download Excel
# ============================================================

@app.get("/api/reports/excel/<filename>")
def download_excel(filename):
    from config import EXPORT_DIR

    file_path = EXPORT_DIR / Path(filename).name

    if not file_path.is_file():
        return jsonify({
            "success": False,
            "error": "Excel file not found",
        }), 404

    return send_file(file_path, as_attachment=True)


# ============================================================
# Play / Download Audio
# ============================================================

@app.get("/api/audio/<filename>")
def play_audio(filename):
    audio_path = VOICE_DIR / Path(filename).name

    if not audio_path.is_file():
        return jsonify({
            "success": False,
            "error": "Recording not found",
        }), 404

    return send_file(
        audio_path,
        as_attachment=False,
    )


# ============================================================
# Process Browser Audio
# ============================================================

@app.route("/api/process-audio", methods=["POST"])
def process_audio():
    try:
        if "audio" not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file received",
            }), 400

        audio_file = request.files["audio"]

        if not audio_file.filename:
            return jsonify({
                "success": False,
                "error": "Empty audio file",
            }), 400

        filename = (
            f"browser_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            f".webm"
        )

        audio_path = VOICE_DIR / filename
        audio_file.save(audio_path)

        print("Audio saved:", audio_path)

        transcription = transcribe_audio_file(audio_path)

        if not transcription:
            return jsonify({
                "success": False,
                "error": "Could not understand the audio",
            }), 400

        return jsonify({
            "success": True,
            "transcription": transcription,
            "audio_file": filename,
            "recorded_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        })

    except Exception as error:
        print("Audio processing error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Mobile App - Process Voice Report
# ============================================================

@app.route("/api/report", methods=["POST"])
def mobile_report():
    try:
        print("MOBILE REPORT REQUEST RECEIVED")

        if "audio" not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file received",
            }), 400

        audio_file = request.files["audio"]

        if not audio_file.filename:
            return jsonify({
                "success": False,
                "error": "Empty audio file",
            }), 400

        speaker_id = request.form.get(
            "speaker_id",
            "mobile_worker",
        ).strip()

        if not speaker_id:
            speaker_id = "mobile_worker"

        safe_speaker_id = secure_filename(speaker_id)

        if not safe_speaker_id:
            safe_speaker_id = "mobile_worker"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{safe_speaker_id}_{timestamp}.m4a"

        audio_path = VOICE_DIR / filename
        audio_file.save(audio_path)

        print("Audio saved:", audio_path)

        transcription = transcribe_audio_file(audio_path)

        if not transcription:
            return jsonify({
                "success": False,
                "error": "Could not understand the audio",
            }), 400

        print("Transcription:", transcription)

        parsed = parse_activity_with_gemini(transcription)

        print("Generated report:", parsed)

        # Do not save here. The user reviews the report first.
        response = {
            "success": True,
            "report": parsed,
            "transcription": transcription,
            "audio_file": filename,
            "activity_id": None,
        }

        print("Mobile report processed successfully")

        return jsonify(response), 200

    except Exception as error:
        print("Mobile report error:", error)

        return jsonify({
            "success": False,
            "error": str(error),
        }), 500


# ============================================================
# Start Server
# ============================================================

# if __name__ == "__main__":
#     app.run(
#         host="0.0.0.0",
#         port=5000,
#         debug=True,
#     )
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    
    