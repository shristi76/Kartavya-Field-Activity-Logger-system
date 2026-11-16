import os
from pathlib import Path

from dotenv import load_dotenv


# ------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------

load_dotenv()


# ------------------------------------------------------------
# Base directories
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"

VOICE_DIR = BASE_DIR / "Voice_Samples"
REPORT_DIR = BASE_DIR / "Generated_Reports"
PHOTO_DIR = DATA_DIR / "photos"


# ------------------------------------------------------------
# Database
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Configure a PostgreSQL connection string.")

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required for secure authentication sessions.")

ADMIN_WORKER_ID = os.getenv("ADMIN_WORKER_ID", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


# ------------------------------------------------------------
# Gemini
# ------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")


# ------------------------------------------------------------
# Create directories
# ------------------------------------------------------------

DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

VOICE_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)
PHOTO_DIR.mkdir(exist_ok=True)


# ------------------------------------------------------------
# Validate configuration
# ------------------------------------------------------------

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file."
    )

if not GEMINI_MODEL:
    raise RuntimeError(
        "GEMINI_MODEL not found in .env file."
    )
