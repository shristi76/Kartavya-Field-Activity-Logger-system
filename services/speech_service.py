import re
import tempfile
from pathlib import Path

import speech_recognition as sr

from config import VOICE_DIR


# --------------------------------------------------
# SAFE FILE NAME
# --------------------------------------------------

def safe_filename(text):
    text = str(text).strip()
    text = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        text
    )
    return text


# --------------------------------------------------
# SAVE AUDIO
# --------------------------------------------------

def save_audio(audio_data, speaker_id):
    speaker_folder = (
        VOICE_DIR / safe_filename(speaker_id)
    )

    speaker_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    from datetime import datetime

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    filename = (
        f"{safe_filename(speaker_id)}_"
        f"{timestamp}.wav"
    )

    audio_path = speaker_folder / filename

    with open(audio_path, "wb") as audio_file:
        audio_file.write(
            audio_data.get_wav_data()
        )

    return audio_path


# --------------------------------------------------
# PREPARE AUDIO FOR SPEECH RECOGNITION
# --------------------------------------------------

def prepare_audio_for_speech_recognition(
    audio_path
):
    """
    Convert phone audio into a clean WAV file
    suitable for Google Speech Recognition.

    Steps:

    M4A
      ↓
    Decode
      ↓
    Mono
      ↓
    Remove long silence
      ↓
    Normalize volume
      ↓
    16 kHz
      ↓
    16-bit WAV
    """

    try:
        from pydub import AudioSegment
        from pydub import effects
        from pydub.silence import detect_nonsilent

    except ImportError as error:
        raise RuntimeError(
            "pydub is required for audio preprocessing. "
            "Install it with: pip install pydub"
        ) from error

    print()
    print("========================================")
    print("AUDIO PREPROCESSING")
    print("========================================")

    print(
        f"Input audio: {audio_path}"
    )

    # --------------------------------------------------
    # LOAD AUDIO
    # --------------------------------------------------

    try:
        audio = AudioSegment.from_file(
            str(audio_path)
        )
    except Exception as error:
        raise RuntimeError(
            f"Could not read audio file: {error}"
        ) from error

    print(
        f"Original channels: {audio.channels}"
    )

    print(
        f"Original sample rate: "
        f"{audio.frame_rate}"
    )

    print(
        f"Original duration: "
        f"{len(audio) / 1000:.2f} seconds"
    )

    print(
        f"Original dBFS: "
        f"{audio.dBFS}"
    )

    print(
        f"Original max dBFS: "
        f"{audio.max_dBFS}"
    )

    # --------------------------------------------------
    # CONVERT TO MONO
    # --------------------------------------------------

    audio = audio.set_channels(1)

    # --------------------------------------------------
    # FIND SPEECH / NON-SILENT PARTS
    # --------------------------------------------------

    print(
        "Detecting speech sections..."
    )

    try:
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=300,
            silence_thresh=-50,
            seek_step=10,
        )
    except Exception as error:
        print(
            "Silence detection failed:",
            error
        )

        nonsilent_ranges = []

    # --------------------------------------------------
    # REMOVE LONG SILENCE
    # --------------------------------------------------

    if nonsilent_ranges:

        print(
            f"Detected "
            f"{len(nonsilent_ranges)} "
            f"audio section(s)."
        )

        chunks = []

        for start, end in nonsilent_ranges:

            # Add a small amount of padding
            # around speech so words don't get cut.
            start = max(
                0,
                start - 200
            )

            end = min(
                len(audio),
                end + 300
            )

            chunks.append(
                audio[start:end]
            )

        if chunks:

            processed_audio = chunks[0]

            for chunk in chunks[1:]:
                processed_audio += chunk

            audio = processed_audio

            print(
                "Silence removed successfully."
            )

    else:

        print(
            "No clear speech sections detected."
        )

        print(
            "Keeping original audio."
        )

    # --------------------------------------------------
    # NORMALIZE VOLUME
    # --------------------------------------------------

    print(
        f"Before normalization dBFS: "
        f"{audio.dBFS}"
    )

    print(
        f"Before normalization peak: "
        f"{audio.max_dBFS}"
    )

    try:

        audio = effects.normalize(
            audio,
            headroom=2.0
        )

        print(
            "Audio normalization successful."
        )

    except Exception as error:

        print(
            "Audio normalization failed:",
            error
        )

    print(
        f"After normalization dBFS: "
        f"{audio.dBFS}"
    )

    print(
        f"After normalization peak: "
        f"{audio.max_dBFS}"
    )

    # --------------------------------------------------
    # OPTIONAL DYNAMIC COMPRESSION
    # --------------------------------------------------

    try:

        audio = audio.compress_dynamic_range(
            threshold=-30.0,
            ratio=3.0,
            attack=5,
            release=50,
        )

        print(
            "Dynamic compression applied."
        )

    except Exception as error:

        print(
            "Compression skipped:",
            error
        )

    # --------------------------------------------------
    # CONVERT TO 16 KHZ MONO
    # --------------------------------------------------

    audio = audio.set_frame_rate(
        16000
    )

    audio = audio.set_sample_width(
        2
    )

    audio = audio.set_channels(
        1
    )

    print(
        f"Final channels: "
        f"{audio.channels}"
    )

    print(
        f"Final sample rate: "
        f"{audio.frame_rate}"
    )

    print(
        f"Final duration: "
        f"{len(audio) / 1000:.2f} seconds"
    )

    print(
        f"Final dBFS: "
        f"{audio.dBFS}"
    )

    print(
        f"Final peak: "
        f"{audio.max_dBFS}"
    )

    # --------------------------------------------------
    # CREATE TEMPORARY WAV
    # --------------------------------------------------

    temporary_file = tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    )

    converted_audio_path = Path(
        temporary_file.name
    )

    temporary_file.close()

    # --------------------------------------------------
    # EXPORT WAV
    # --------------------------------------------------

    try:

        audio.export(
            str(converted_audio_path),
            format="wav"
        )

    except Exception as error:

        converted_audio_path.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            f"Could not export WAV audio: "
            f"{error}"
        ) from error

    print(
        "Processed WAV created:"
    )

    print(
        converted_audio_path
    )

    print(
        f"WAV size: "
        f"{converted_audio_path.stat().st_size} bytes"
    )

    print(
        "========================================"
    )

    return converted_audio_path


# --------------------------------------------------
# TRANSCRIBE AUDIO FILE
# --------------------------------------------------

def transcribe_audio_file(audio_path):

    recognizer = sr.Recognizer()

    converted_audio_path = None

    try:

        audio_path = Path(audio_path)

        print()
        print("========================================")
        print("SPEECH RECOGNITION")
        print("========================================")

        print(
            f"Audio file: {audio_path}"
        )

        print(
            f"Exists: {audio_path.exists()}"
        )

        if not audio_path.exists():

            raise RuntimeError(
                "Audio file does not exist."
            )

        print(
            f"File size: "
            f"{audio_path.stat().st_size} bytes"
        )

        # --------------------------------------------------
        # PREPARE AUDIO
        # --------------------------------------------------

        converted_audio_path = (
            prepare_audio_for_speech_recognition(
                audio_path
            )
        )

        # --------------------------------------------------
        # READ WAV
        # --------------------------------------------------

        print()
        print(
            "Reading processed WAV audio..."
        )

        with sr.AudioFile(
            str(converted_audio_path)
        ) as source:

            audio = recognizer.record(
                source
            )

        print(
            "Processed audio loaded."
        )

        # --------------------------------------------------
        # GOOGLE SPEECH RECOGNITION
        # --------------------------------------------------

        print()
        print(
            "Sending audio to Google "
            "Speech Recognition..."
        )

        print(
            "Language: hi-IN"
        )

        try:

            text = recognizer.recognize_google(
                audio,
                language="hi-IN"
            )

        except sr.UnknownValueError:

            print()
            print(
                "Google Speech Recognition "
                "could not understand the audio."
            )

            raise RuntimeError(
                "Could not understand the Hindi speech. "
                "Please speak clearly and make sure "
                "the recording contains speech."
            )

        except sr.RequestError as error:

            print()
            print(
                "Google Speech Recognition "
                "service error:"
            )

            print(error)

            raise RuntimeError(
                f"Speech recognition service error: "
                f"{error}"
            )

        # --------------------------------------------------
        # SUCCESS
        # --------------------------------------------------

        print()
        print(
            "========================================"
        )

        print(
            "TRANSCRIPTION SUCCESSFUL"
        )

        print(
            "========================================"
        )

        print(
            f"Hindi text: {text}"
        )

        print(
            "========================================"
        )

        return text

    finally:

        # --------------------------------------------------
        # DELETE TEMP WAV
        # --------------------------------------------------

        if converted_audio_path:

            try:

                converted_audio_path.unlink(
                    missing_ok=True
                )

                print(
                    "Temporary WAV deleted."
                )

            except Exception as error:

                print(
                    "Could not delete temporary WAV:",
                    error
                )


# --------------------------------------------------
# COMPUTER MICROPHONE RECORDING
# --------------------------------------------------

def capture_microphone_audio(
    speaker_id
):

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

        # --------------------------------------------------
        # SAVE AUDIO
        # --------------------------------------------------

        audio_path = save_audio(
            audio_data,
            speaker_id
        )

        # --------------------------------------------------
        # RECOGNIZE
        # --------------------------------------------------

        hindi_text = recognizer.recognize_google(
            audio_data,
            language="hi-IN"
        )

        return (
            hindi_text,
            audio_path
        )

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
            f"Speech recognition service error: "
            f"{error}"
        )