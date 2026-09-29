import json

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL


client = genai.Client(
    api_key=GEMINI_API_KEY
)

AVAILABLE_MODELS = list(dict.fromkeys([
    GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.0-flash"
]))


def parse_activity_with_gemini(hindi_text):
    """
    Translate Hindi field activity text and extract
    structured information.
    """

    prompt = f"""
You are an AI assistant for a field activity
logging system used by community and social workers.

The worker has provided a field activity statement in Hindi.

Your task:

1. Translate the complete Hindi statement into clear English.
2. Identify the main activity.
3. Identify the beneficiaries.
4. Identify the location.
5. Preserve important information.
6. Do not invent information.
7. Do not assume missing information.
8. If something is not mentioned, return "Not mentioned".
9. Keep numbers accurate.
10. Keep names and locations accurate.

Return ONLY valid JSON.

Use exactly this structure:

{{
    "translated_text": "...",
    "activity": "...",
    "beneficiaries": "...",
    "location": "..."
}}

Hindi statement:

{hindi_text}
"""

    try:

        response = None
        last_error = None

        for model in AVAILABLE_MODELS:

            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt
                )
                break

            except Exception as error:
                last_error = error

        if response is None and last_error:
            raise RuntimeError(
                f"All Gemini models failed: {last_error}"
            ) from last_error

        if not response:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        if not response.text:

            raise RuntimeError(
                "Gemini returned no text."
            )

        raw_text = response.text.strip()

        # Remove markdown fences if returned
        if raw_text.startswith("```json"):

            raw_text = raw_text[7:]

        elif raw_text.startswith("```"):

            raw_text = raw_text[3:]

        if raw_text.endswith("```"):

            raw_text = raw_text[:-3]

        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        required_fields = [
            "translated_text",
            "activity",
            "beneficiaries",
            "location"
        ]

        for field in required_fields:

            if field not in data:

                raise RuntimeError(
                    f"Gemini response missing field: {field}"
                )

            if data[field] is None:

                data[field] = "Not mentioned"

            else:

                data[field] = str(
                    data[field]
                ).strip()

        return data

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"Gemini returned invalid JSON: {error}"
        )

    except Exception as error:

        raise RuntimeError(
            f"Gemini processing failed: {error}"
        )