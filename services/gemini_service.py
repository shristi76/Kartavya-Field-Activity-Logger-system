
import json
import logging

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL


# ============================================================
# CONFIGURATION
# ============================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is missing. Configure it in your environment."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

AVAILABLE_MODELS = list(dict.fromkeys([
    GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]))

# Numeric fields are separate from TEXT_FIELDS.
# Keep these only if your application still uses these metrics.
NUMERIC_FIELDS = [
    "people_visited",
    "households_visited",
    "beneficiaries_assisted",
]

# Your selected text fields.
TEXT_FIELDS = [
    "worker_name",
    "date",
    "location",
    "organization",
    "district",
    "translated_text",
    "activity",
    "additional_notes",
]

ALL_FIELDS = TEXT_FIELDS + NUMERIC_FIELDS


# ============================================================
# STRUCTURED JSON SCHEMA
# ============================================================

# The numeric fields are nullable so unknown counts can be null.
REPORT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        field: {
            "type": "INTEGER",
            "nullable": True,
        }
        for field in NUMERIC_FIELDS
    } | {
        field: {
            "type": "STRING",
        }
        for field in TEXT_FIELDS
    },
    "required": ALL_FIELDS,
}


# ============================================================
# PROMPT
# ============================================================

def build_prompt(hindi_text):
    """Build instructions for extracting the selected report fields."""

    return f"""
You are an expert assistant for a social-work field reporting
system in India.

The worker may speak Hindi, Hinglish, or English.

Read the complete statement and return one JSON object matching
the supplied schema. Extract only the requested fields.

GENERAL RULES:

1. Understand natural spoken Hindi, Hinglish, and common
   social-work terminology.
2. Translate the complete statement faithfully into English
   in translated_text.
3. Never invent, guess, or assume facts.
4. For missing text fields, return an empty string "".
5. For missing numeric fields, return null.
6. Numeric fields must be integers or null, never strings.
7. Preserve names, dates, quantities, and locations.
8. Distinguish people spoken to from households visited.
9. Count beneficiaries only when the statement explicitly
   supports the number of people who received assistance.
10. Do not claim a service, benefit, or assistance was provided
    when it was only requested, discussed, or planned.
11. Do not infer eligibility for government schemes.
12. Preserve uncertainty and ambiguity instead of guessing.
13. Use respectful, neutral English.
14. Do not return "Not mentioned", "Unknown", or "N/A" for
    missing text fields. Use an empty string instead.
15. Return every field required by the schema.
16. Do not include Markdown fences or explanatory text outside
    the JSON object.

FIELD INSTRUCTIONS:

worker_name:
The name of the social worker, if explicitly stated.

date:
The date of the reported activity. Prefer YYYY-MM-DD.
Use the date explicitly stated in the input. Do not substitute
today's date when the activity date is missing.
Resolve relative dates only when the reference date is clear.

location:
The general location where the activity occurred. Include
explicitly stated location details, but do not invent missing
place names.

organization:
The name of the organization, if explicitly stated.

district:
The district name, if explicitly stated. Do not confuse a
village, block, city, or state with a district.

translated_text:
Translate the entire statement into clear, natural English.
Preserve all important facts, names, numbers, locations,
problems, actions, plans, and uncertainty. Do not add facts
that were not in the original statement.

activity:
Give a concise description of the main activity, such as
school inspection, household visits, community awareness,
counselling, or a welfare survey. Base it on the statement.



beneficiaries_assisted:
The number of distinct people explicitly stated to have received
assistance. Do not count everyone visited, interviewed, or
identified as having a problem. If the number of recipients
cannot be established, return null.

CLASSIFICATION EXAMPLE:

Input:
"मेरा नाम सुनीता देवी है। मैंने 13 अक्टूबर 2026 को पटना
जिले में आठ परिवारों से मुलाकात की और बारह लोगों से बात की।
तीन परिवारों ने राशन कार्ड की समस्या बताई।"

Expected interpretation:
- worker_name: Sunita Devi
- date: 2026-10-13
- district: Patna
- people_visited: 12
- households_visited: 8
- beneficiaries_assisted: null, because the statement does not
  establish how many people actually received assistance
- translated_text: A faithful English translation of the
  complete input statement
- activity: Household visits and discussions with community
  members
- organization: empty string if not stated
- location: include only location details supported by the input
- additional_notes: empty string if no additional information
  needs to be recorded

Do not copy example values into the actual report unless the
actual statement supports them.

STATEMENT TO PROCESS:
{hindi_text}
"""


# ============================================================
# NORMALIZE AND VALIDATE GEMINI RESPONSE
# ============================================================

def normalize_report(data, original_text):
    """
    Ensure the report contains all selected fields with
    consistent types and missing-value handling.
    """

    if not isinstance(data, dict):
        raise ValueError(
            "Gemini response must be a JSON object."
        )

    result = {}

    for field in ALL_FIELDS:
        value = data.get(field)

        if field in NUMERIC_FIELDS:
            if value is None or value == "":
                result[field] = None

            elif isinstance(value, bool):
                logger.warning(
                    "Boolean supplied for numeric field %s",
                    field,
                )
                result[field] = None

            elif isinstance(value, int):
                result[field] = value

            elif (
                isinstance(value, float)
                and value.is_integer()
            ):
                result[field] = int(value)

            else:
                logger.warning(
                    "Invalid numeric value for %s: %r",
                    field,
                    value,
                )
                result[field] = None

        else:
            if value is None:
                result[field] = ""

            elif isinstance(value, str):
                result[field] = value.strip()

            else:
                logger.warning(
                    "Unexpected non-string value for %s: %r",
                    field,
                    value,
                )
                result[field] = str(value).strip()

    # A translation should not be fabricated if the model fails
    # to provide one. Keep the missing value empty.
    result["translated_text"] = (
        result["translated_text"].strip()
    )

    return result


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def parse_activity_with_gemini(hindi_text):
    """
    Translate a Hindi/Hinglish statement and extract the
    selected social-work report fields.

    Returns:
        dict: Validated report data.

    Raises:
        ValueError: If the input statement is empty.
        RuntimeError: If every configured model fails.
    """

    if (
        not isinstance(hindi_text, str)
        or not hindi_text.strip()
    ):
        raise ValueError(
            "The statement must not be empty."
        )

    prompt = build_prompt(hindi_text.strip())
    errors = []

    for model in AVAILABLE_MODELS:
        try:
            logger.info(
                "Trying Gemini model: %s",
                model,
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=REPORT_SCHEMA,
                    temperature=0.1,
                ),
            )

            raw_text = response.text

            if not raw_text or not raw_text.strip():
                raise ValueError(
                    "Gemini returned an empty response."
                )

            data = json.loads(raw_text.strip())

            report = normalize_report(
                data,
                hindi_text.strip(),
            )

            logger.info(
                "Successfully extracted report using %s",
                model,
            )

            return report

        except Exception as error:
            logger.exception(
                "Extraction failed using model %s",
                model,
            )

            errors.append(
                f"{model}: {error}"
            )

    raise RuntimeError(
        "All configured Gemini models failed. Details: "
        + " | ".join(errors)
    )
