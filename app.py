from pathlib import Path
import os
from datetime import datetime

from flask import (
    Flask,
    jsonify,
    render_template,
    request,
    send_file
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
    delete_log
)

from services.gemini_service import (
    parse_activity_with_gemini
)

from services.report_service import (
    generate_pdf,
    generate_excel
)

from services.speech_service import (
    transcribe_audio_file
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}


# ------------------------------------------------------------
# Initialize database
# ------------------------------------------------------------

initialize_database()


# ------------------------------------------------------------
# Frontend
# ------------------------------------------------------------

@app.get("/")
def home():

    return render_template(
        "index.html"
    )


# ------------------------------------------------------------
# Health check
# ------------------------------------------------------------

@app.get("/api/health")
def health():

    return jsonify({
        "success": True,
        "message": "Field Activity API is running"
    })


# ------------------------------------------------------------
# Get recent logs
# ------------------------------------------------------------

@app.get("/api/activities")
def get_activities():

    try:

        limit = request.args.get(
            "limit",
            default=20,
            type=int
        )

        limit = min(
            max(limit, 1),
            100
        )

        logs = get_recent_logs(
            limit
        )

        return jsonify({
            "success": True,
            "data": [
                dict(log)
                for log in logs
            ]
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ------------------------------------------------------------
# Get single activity
# ------------------------------------------------------------

@app.get("/api/activities/<int:log_id>")
def get_activity(log_id):

    log = get_log_by_id(
        log_id
    )

    if not log:

        return jsonify({
            "success": False,
            "error": "Activity not found"
        }), 404

    return jsonify({
        "success": True,
        "data": dict(log)
    })


# ------------------------------------------------------------
# Process Hindi text
# ------------------------------------------------------------

@app.post("/api/process")
def process_activity():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "error": "Invalid JSON request"
        }), 400

    hindi_text = data.get(
        "hindi_text",
        ""
    ).strip()

    if not hindi_text:

        return jsonify({
            "success": False,
            "error": "Hindi text is required"
        }), 400

    try:

        result = parse_activity_with_gemini(
            hindi_text
        )

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ------------------------------------------------------------
# Save activity
# ------------------------------------------------------------

@app.post("/api/activities")
def create_activity():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "error": "Invalid JSON request"
        }), 400

    speaker_id = str(
        data.get(
            "speaker_id",
            ""
        )
    ).strip()

    hindi_text = str(
        data.get(
            "hindi_text",
            ""
        )
    ).strip()

    if not speaker_id:

        return jsonify({
            "success": False,
            "error": "Speaker ID is required"
        }), 400

    if not hindi_text:

        return jsonify({
            "success": False,
            "error": "Hindi text is required"
        }), 400

    try:

        parsed = parse_activity_with_gemini(
            hindi_text
        )

        reviewed_fields = [
            "translated_text",
            "activity",
            "beneficiaries",
            "location"
        ]

        for field in reviewed_fields:

            reviewed_value = str(
                data.get(
                    field,
                    parsed[field]
                )
            ).strip()

            if reviewed_value:
                parsed[field] = reviewed_value

        log_id = save_log(
            speaker_id=speaker_id,
            audio_file=data.get(
                "audio_file"
            ),
            hindi_text=hindi_text,
            translated_text=parsed[
                "translated_text"
            ],
            activity=parsed[
                "activity"
            ],
            beneficiaries=parsed[
                "beneficiaries"
            ],
            location=parsed[
                "location"
            ],
            photo_file=data.get(
                "photo_file"
            )
        )

        return jsonify({
            "success": True,
            "message": "Activity saved successfully",
            "data": {
                "id": log_id,
                "speaker_id": speaker_id,
                "hindi_text": hindi_text,
                **parsed
            }
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ------------------------------------------------------------
# Upload activity photo
# ------------------------------------------------------------

@app.post("/api/uploads/photo")
def upload_photo():

    photo = request.files.get("photo")

    if not photo or not photo.filename:
        return jsonify({
            "success": False,
            "error": "Please select a photo"
        }), 400

    extension = Path(photo.filename).suffix.lower().lstrip(".")

    if extension not in ALLOWED_PHOTO_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "Only JPG and PNG photos are supported"
        }), 400

    try:
        photo.stream.seek(0)
        with Image.open(photo.stream) as image:
            image.verify()
        photo.stream.seek(0)
    except (UnidentifiedImageError, OSError):
        return jsonify({
            "success": False,
            "error": "The selected file is not a valid photo"
        }), 400

    safe_name = secure_filename(photo.filename)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_name}"
    output_path = PHOTO_DIR / filename
    photo.save(output_path)

    return jsonify({
        "success": True,
        "data": {
            "filename": filename
        }
    })


# ------------------------------------------------------------
# Delete activity
# ------------------------------------------------------------

@app.delete("/api/activities/<int:log_id>")
def remove_activity(log_id):

    deleted = delete_log(
        log_id
    )

    if not deleted:

        return jsonify({
            "success": False,
            "error": "Activity not found"
        }), 404

    return jsonify({
        "success": True,
        "message": "Activity deleted"
    })


# ------------------------------------------------------------
# Generate report
# ------------------------------------------------------------

@app.post("/api/reports")
def create_report():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify({
            "success": False,
            "error": "Invalid request"
        }), 400

    start_date = str(
        data.get(
            "start_date",
            ""
        )
    ).strip()

    end_date = str(
        data.get(
            "end_date",
            ""
        )
    ).strip()

    speaker_id = str(
        data.get(
            "speaker_id",
            ""
        )
    ).strip()

    if not start_date or not end_date:

        return jsonify({
            "success": False,
            "error": "Start date and end date are required"
        }), 400

    logs = get_logs_between(
        start_date,
        end_date,
        speaker_id or None
    )

    if not logs:

        return jsonify({
            "success": False,
            "error": "No logs found for this period"
        }), 404

    try:

        pdf_path = generate_pdf(
            logs=logs,
            start_date=start_date,
            end_date=end_date,
            speaker_id=speaker_id or None
        )

        excel_path = generate_excel(
            logs=logs,
            start_date=start_date,
            end_date=end_date
        )

        return jsonify({
            "success": True,
            "message": "Reports generated successfully",
            "data": {
                "pdf": pdf_path.name,
                "excel": excel_path.name,
                "generated_at": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            }
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ------------------------------------------------------------
# Download PDF
# ------------------------------------------------------------

@app.get("/api/reports/pdf/<filename>")
def download_pdf(filename):

    from config import REPORT_DIR

    file_path = REPORT_DIR / Path(
        filename
    ).name

    if not file_path.exists():

        return jsonify({
            "success": False,
            "error": "PDF not found"
        }), 404

    return send_file(
        file_path,
        as_attachment=True
    )


# ------------------------------------------------------------
# Download Excel
# ------------------------------------------------------------

@app.get("/api/reports/excel/<filename>")
def download_excel(filename):

    from config import EXPORT_DIR

    file_path = EXPORT_DIR / Path(
        filename
    ).name

    if not file_path.exists():

        return jsonify({
            "success": False,
            "error": "Excel file not found"
        }), 404

    return send_file(
        file_path,
        as_attachment=True
    )


@app.get("/api/audio/<filename>")
def play_audio(filename):

    audio_path = BASE_DIR / "Voice_Samples" / Path(
        filename
    ).name

    if not audio_path.exists():

        return jsonify({
            "success": False,
            "error": "Recording not found"
        }), 404

    return send_file(
        audio_path,
        as_attachment=False
    )


@app.route("/api/process-audio", methods=["POST"])
def process_audio():
    try:
        if "audio" not in request.files:
            return jsonify({
                "error": "No audio file received"
            }), 400

        audio_file = request.files["audio"]

        if audio_file.filename == "":
            return jsonify({
                "error": "Empty audio file"
            }), 400

        # Save temporary audio
        filename = f"browser_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.webm"
        audio_path = os.path.join("Voice_Samples", filename)

        os.makedirs("Voice_Samples", exist_ok=True)

        audio_file.save(audio_path)

        # Transcribe audio
        transcription = transcribe_audio_file(audio_path)

        if not transcription:
            return jsonify({
                "error": "Could not understand the audio"
            }), 400

        return jsonify({
            "success": True,
            "transcription": transcription,
            "audio_file": filename,
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        print("Audio processing error:", e)

        return jsonify({
            "error": str(e)
        }), 500

# ------------------------------------------------------------
# Start server
# ------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
    
