// import os
// from datetime import datetime

// from flask import (
//     Flask,
//     jsonify,
//     request,
//     send_from_directory
// )

// from flask_cors import CORS

// from config import REPORT_DIR

// from services.speech_service import (
//     save_uploaded_audio,
//     transcribe_audio_file
// )

// from services.gemini_service import (
//     parse_activity_with_gemini
// )

// from services.report_service import (
//     generate_pdf
// )


// # ==========================================================
// # APP
// # ==========================================================

// app = Flask(__name__)

// CORS(app)


// # ==========================================================
// # CONFIGURATION
// # ==========================================================

// app.config["MAX_CONTENT_LENGTH"] = (
//     25 * 1024 * 1024
// )


// # ==========================================================
// # HEALTH CHECK
// # ==========================================================

// @app.route(
//     "/api/health",
//     methods=["GET"]
// )
// def health():

//     return jsonify({
//         "success": True,
//         "message": "Hospital Field Worker API is running"
//     })


// # ==========================================================
// # CREATE REPORT
// # ==========================================================

// @app.route(
//     "/api/report",
//     methods=["POST"]
// )
// def create_report():

//     try:

//         # --------------------------------------------------
//         # CHECK AUDIO
//         # --------------------------------------------------

//         if "audio" not in request.files:

//             return jsonify({
//                 "success": False,
//                 "message": "No audio file received."
//             }), 400

//         audio_file = request.files["audio"]

//         if not audio_file.filename:

//             return jsonify({
//                 "success": False,
//                 "message": "Audio filename is missing."
//             }), 400

//         # --------------------------------------------------
//         # WORKER ID
//         # --------------------------------------------------

//         speaker_id = (
//             request.form.get(
//                 "speaker_id"
//             )
//             or "mobile_worker"
//         )

//         # --------------------------------------------------
//         # SAVE AUDIO
//         # --------------------------------------------------

//         audio_path = save_uploaded_audio(
//             audio_file,
//             speaker_id
//         )

//         print(
//             f"Audio saved: {audio_path}"
//         )

//         # --------------------------------------------------
//         # SPEECH TO TEXT
//         # --------------------------------------------------

//         hindi_text = transcribe_audio_file(
//             audio_path
//         )

//         print(
//             f"Hindi text: {hindi_text}"
//         )

//         if not hindi_text:

//             return jsonify({
//                 "success": False,
//                 "message": "Could not understand the voice recording."
//             }), 400

//         # --------------------------------------------------
//         # GEMINI
//         # --------------------------------------------------

//         parsed_data = (
//             parse_activity_with_gemini(
//                 hindi_text
//             )
//         )

//         print(
//             f"Gemini result: {parsed_data}"
//         )

//         # --------------------------------------------------
//         # CREATE LOG OBJECT
//         # --------------------------------------------------

//         created_at = datetime.now().strftime(
//             "%Y-%m-%d %H:%M:%S"
//         )

//         log = {

//             "created_at": created_at,

//             "speaker_id": speaker_id,

//             "audio_file": str(
//                 audio_path
//             ),

//             "hindi_text": hindi_text,

//             "worker_name": parsed_data.get(
//                 "worker_name",
//                 "Not mentioned"
//             ),

//             "date": parsed_data.get(
//                 "date",
//                 "Not mentioned"
//             ),

//             "location": parsed_data.get(
//                 "location",
//                 "Not mentioned"
//             ),

//             "health_center": parsed_data.get(
//                 "health_center",
//                 "Not mentioned"
//             ),

//             "village": parsed_data.get(
//                 "village",
//                 "Not mentioned"
//             ),

//             "district": parsed_data.get(
//                 "district",
//                 "Not mentioned"
//             ),

//             "translated_text": parsed_data.get(
//                 "translated_text",
//                 "Not mentioned"
//             ),

//             "activity": parsed_data.get(
//                 "activity",
//                 "Not mentioned"
//             ),

//             "beneficiaries": (
//                 parsed_data.get(
//                     "people_visited"
//                 )
//                 or parsed_data.get(
//                     "beneficiaries",
//                     "Not mentioned"
//                 )
//             ),

//             "people_visited": parsed_data.get(
//                 "people_visited"
//             ),

//             "patients_with_fever": parsed_data.get(
//                 "patients_with_fever"
//             ),

//             "patients_with_high_bp": parsed_data.get(
//                 "patients_with_high_bp"
//             ),

//             "patients_with_low_bp": parsed_data.get(
//                 "patients_with_low_bp"
//             ),

//             "patients_with_weakness": parsed_data.get(
//                 "patients_with_weakness"
//             ),

//             "patients_with_diabetes": parsed_data.get(
//                 "patients_with_diabetes"
//             ),

//             "symptoms_reported": parsed_data.get(
//                 "symptoms_reported",
//                 "Not mentioned"
//             ),

//             "advice_given": parsed_data.get(
//                 "advice_given",
//                 "Not mentioned"
//             ),

//             "medicines_given": parsed_data.get(
//                 "medicines_given",
//                 "Not mentioned"
//             ),

//             "referral_required": parsed_data.get(
//                 "referral_required",
//                 "Not mentioned"
//             ),

//             "additional_notes": parsed_data.get(
//                 "additional_notes",
//                 "Not mentioned"
//             ),

//             "photo_file": None
//         }

//         # --------------------------------------------------
//         # GENERATE PDF
//         # --------------------------------------------------

//         today = datetime.now().strftime(
//             "%Y-%m-%d"
//         )

//         pdf_path = generate_pdf(
//             logs=[log],
//             start_date=today,
//             end_date=today,
//             speaker_id=speaker_id
//         )

//         # --------------------------------------------------
//         # PDF URL
//         # --------------------------------------------------

//         pdf_url = None

//         if pdf_path:

//             pdf_url = (
//                 "/Generated_Reports/"
//                 + pdf_path.name
//             )

//         # --------------------------------------------------
//         # RESPONSE
//         # --------------------------------------------------

//         return jsonify({

//             "success": True,

//             "message": (
//                 "Voice processed successfully."
//             ),

//             "hindi_text": hindi_text,

//             "report": {

//                 "worker_name":
//                     parsed_data.get(
//                         "worker_name"
//                     ),

//                 "date":
//                     parsed_data.get(
//                         "date"
//                     ),

//                 "location":
//                     parsed_data.get(
//                         "location"
//                     ),

//                 "health_center":
//                     parsed_data.get(
//                         "health_center"
//                     ),

//                 "village":
//                     parsed_data.get(
//                         "village"
//                     ),

//                 "district":
//                     parsed_data.get(
//                         "district"
//                     ),

//                 "activity":
//                     parsed_data.get(
//                         "activity"
//                     ),

//                 "people_visited":
//                     parsed_data.get(
//                         "people_visited"
//                     ),

//                 "patients_with_fever":
//                     parsed_data.get(
//                         "patients_with_fever"
//                     ),

//                 "patients_with_high_bp":
//                     parsed_data.get(
//                         "patients_with_high_bp"
//                     ),

//                 "patients_with_low_bp":
//                     parsed_data.get(
//                         "patients_with_low_bp"
//                     ),

//                 "patients_with_weakness":
//                     parsed_data.get(
//                         "patients_with_weakness"
//                     ),

//                 "patients_with_diabetes":
//                     parsed_data.get(
//                         "patients_with_diabetes"
//                     ),

//                 "symptoms_reported":
//                     parsed_data.get(
//                         "symptoms_reported"
//                     ),

//                 "advice_given":
//                     parsed_data.get(
//                         "advice_given"
//                     ),

//                 "medicines_given":
//                     parsed_data.get(
//                         "medicines_given"
//                     ),

//                 "referral_required":
//                     parsed_data.get(
//                         "referral_required"
//                     ),

//                 "additional_notes":
//                     parsed_data.get(
//                         "additional_notes"
//                     )
//             },

//             "pdf_url": pdf_url

//         })

//     except Exception as error:

//         print(
//             f"ERROR /api/report: {error}"
//         )

//         return jsonify({

//             "success": False,

//             "message": str(error)

//         }), 500


// # ==========================================================
// # PDF FILE
// # ==========================================================

// @app.route(
//     "/Generated_Reports/<path:filename>",
//     methods=["GET"]
// )
// def download_report(filename):

//     return send_from_directory(
//         REPORT_DIR,
//         filename
//     )


// # ==========================================================
// # RUN
// # ==========================================================

// if __name__ == "__main__":

//     print(
//         "\n======================================"
//     )

//     print(
//         "Hospital Field Worker API"
//     )

//     print(
//         "======================================"
//     )

//     print(
//         "Server: http://0.0.0.0:5000"
//     )

//     print(
//         "Health: http://localhost:5000/api/health"
//     )

//     print(
//         "======================================\n"
//     )

//     app.run(
//         host="0.0.0.0",
//         port=5000,
//         debug=True
//     )