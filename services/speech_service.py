import re
import tempfile
from pathlib import Path

import speech_recognition as sr


from config import VOICE_DIR


def safe_filename(text):
    """
    Convert text into a safe filename.
    """

    text = str(text).strip()

    text = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        text
    )

    return text


def save_audio(
    audio_data,
    speaker_id
):
    """
    Save microphone audio as WAV.
    """

    speaker_folder = (
        VOICE_DIR /
        safe_filename(speaker_id)
    )

    speaker_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    from datetime import datetime

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"{safe_filename(speaker_id)}_"
        f"{timestamp}.wav"
    )

    audio_path = speaker_folder / filename

    with open(
        audio_path,
        "wb"
    ) as audio_file:

        audio_file.write(
            audio_data.get_wav_data()
        )

    return audio_path


def transcribe_audio_file(audio_path):
    """
    Convert WAV audio to Hindi text.
    """

    recognizer = sr.Recognizer()
    converted_audio_path = None

    if Path(audio_path).suffix.lower() not in {".wav", ".aiff", ".aif", ".flac"}:
        try:
            from pydub import AudioSegment
        except ImportError as error:
            raise RuntimeError(
                "Browser audio conversion requires pydub. Install the project requirements."
            ) from error

        temporary_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )
        converted_audio_path = Path(temporary_file.name)
        temporary_file.close()

        try:
            AudioSegment.from_file(str(audio_path)).export(
                str(converted_audio_path),
                format="wav"
            )
            audio_path = converted_audio_path
        except Exception as error:
            converted_audio_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Could not convert browser audio: {error}"
            ) from error

    try:

        with sr.AudioFile(
            str(audio_path)
        ) as source:

            audio = recognizer.record(
                source
            )

        text = recognizer.recognize_google(
            audio,
            language="hi-IN"
        )

        return text

    except sr.UnknownValueError:

        raise RuntimeError(
            "Could not understand the Hindi speech."
        )

    except sr.RequestError as error:

        raise RuntimeError(
            f"Speech recognition service error: {error}"
        )

    finally:

        if converted_audio_path:
            converted_audio_path.unlink(missing_ok=True)


def capture_microphone_audio(
    speaker_id
):
    """
    Capture Hindi speech from microphone.

    This function is mainly useful for testing
    the backend locally.
    """

    recognizer = sr.Recognizer()

    recognizer.energy_threshold = 250

    recognizer.dynamic_energy_threshold = True

    recognizer.pause_threshold = 2.0

    recognizer.non_speaking_duration = 0.8

    recognizer.phrase_threshold = 0.3

    try:

        with sr.Microphone() as source:

            print(
                "Adjusting for background noise..."
            )

            recognizer.adjust_for_ambient_noise(
                source,
                duration=1
            )

            print(
                "Speak in Hindi..."
            )

            audio_data = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=90
            )

        audio_path = save_audio(
            audio_data,
            speaker_id
        )

        hindi_text = recognizer.recognize_google(
            audio_data,
            language="hi-IN"
        )

        return hindi_text, audio_path

    except sr.WaitTimeoutError:

        raise RuntimeError(
            "No speech detected."
        )

    except sr.UnknownValueError:

        raise RuntimeError(
            "Could not understand the Hindi speech."
        )

    except sr.RequestError as error:

        raise RuntimeError(
            f"Speech recognition service error: {error}"
        )