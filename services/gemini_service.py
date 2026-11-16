# """Translate field-worker transcripts and extract a complete field report."""

# import json
# import logging

# from google import genai
# from google.genai import types

# from config import GEMINI_API_KEY, GEMINI_MODEL

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# if not GEMINI_API_KEY:
#     raise ValueError("GEMINI_API_KEY is missing. Configure it in your environment.")

# client = genai.Client(api_key=GEMINI_API_KEY)
# AVAILABLE_MODELS = list(dict.fromkeys([
#     GEMINI_MODEL,
#     "gemini-2.5-flash",
#     "gemini-2.0-flash",
# ]))

# # Keep these names aligned with mobile/src/types/report.ts and ReportCard.tsx.
# TEXT_FIELDS = [
#     "worker_name", "date", "location", "organization", "village", "block",
#     "district", "activity", "issues_identified",
#     "education_related_issues", "health_and_wellbeing_concerns",
#     "family_and_child_welfare_concerns", "livelihood_and_financial_issues",
#     "government_scheme_and_benefit_issues",
#     "elderly_and_disability_support_needs", "assistance_provided",
#     "actions_taken", "referrals_made", "services_or_benefits_accessed",
#     "referral_required", "follow_up_required", "follow_up_date",
#     "responsible_person", "outcomes_and_progress", "translated_text",
#     "additional_notes",
# ]
# NUMERIC_FIELDS = ["people_visited", "households_visited", "beneficiaries_assisted"]
# ALL_FIELDS = TEXT_FIELDS + NUMERIC_FIELDS

# REPORT_SCHEMA = {
#     "type": "OBJECT",
#     "properties": {
#         **{field: {"type": "STRING"} for field in TEXT_FIELDS},
#         **{field: {"type": "INTEGER", "nullable": True} for field in NUMERIC_FIELDS},
#     },
#     "required": ALL_FIELDS,
# }


# def build_prompt(transcript):
#     """Give Gemini field-by-field rules tailored to Hindi field reports."""
#     return f"""You extract structured reports from social-work field-worker speech in India.
# The transcript may be Hindi, Hinglish, or English, and may contain speech-recognition errors.
# Understand the meaning from context but never repair uncertainty by inventing facts.

# Return one JSON object matching the supplied schema, with every required key.
# For absent or unclear text use an empty string. For absent or unclear counts use null.
# All text values must be English. Keep names as spoken (use a sensible English transliteration
# for Hindi names). Prefer YYYY-MM-DD for dates only when the date is unambiguous. Never use
# today's date to fill a missing activity date. Do not include Markdown or explanation.

# EXTRACTION RULES:
# - translated_text: faithful, complete English translation of the whole transcript. Preserve
#   names, places, numbers, concerns, actions, requests, plans, outcomes, and uncertainty.
# - worker_name: the reporting worker's name only when explicitly stated; do not substitute
#   the speaker ID or the name of a person visited.
# - location, village, block, district: extract each geographic level separately only when
#   stated. A village/city is not automatically a block or district. location may combine the
#   explicitly stated visit place details without adding inferred geography.
# - organization: explicitly named employer/organization only.
# - activity: concise main work performed (for example, household visit, counselling,
#   awareness session, school visit, or survey). Distinguish completed work from intended work.
# - people_visited: number of distinct people personally visited/met/spoken with, only when
#   explicitly countable. Do not copy household or beneficiary counts into this field.
# - households_visited: number of households/families visited, only when explicitly countable.
# - beneficiaries_assisted: number of people . Use null if recipients/count are not explicit.
# - issues_identified: concise summary of all explicitly stated problems/needs. Also put each
#   issue in its matching category below; do not omit a concern because it is categorized.
# - education_related_issues: schooling, attendance, learning, education access, or school needs.
# - health_and_wellbeing_concerns: physical/mental health, treatment, nutrition, wellbeing.
# - family_and_child_welfare_concerns: child protection, family safety, caregiving, family needs.
# - livelihood_and_financial_issues: work, income, debt, housing/basic-needs affordability.
# - government_scheme_and_benefit_issues: scheme/benefit application, eligibility question,
#   access barrier, ration card, pension, or other government support. Do not infer eligibility.
# - elderly_and_disability_support_needs: explicitly stated elderly or disability-related needs.
# - assistance_provided: concrete support actually delivered. Keep requests and planned support
#   out of this field.
# - actions_taken: completed steps taken by the worker (including assessment or contact).
# - referrals_made: referrals that were actually made, with destination if stated.
# - services_or_benefits_accessed: services/benefits the person actually obtained or used.
# - referral_required: whether a referral is explicitly needed/planned, and to where if stated.
# - follow_up_required: explicit follow-up need or plan; distinguish this from completed action.
# - follow_up_date: date for the planned follow-up only, not the activity date.
# - responsible_person: explicitly identified person responsible for follow-up/action.
# - outcomes_and_progress: explicit result/progress, not a predicted result.
# - additional_notes: relevant explicit details that do not fit the other fields. Do not repeat
#   the entire translation here.

# Do not turn a discussion, request, intention, or need into a completed action or outcome.
# Do not assume that a whole family received help because one member did. Do not infer counts
# from vague plurals such as "many". Preserve approximate counts as null if schema only permits
# an integer and no exact count is given. Keep separate facts in the correct separate fields.

# TRANSCRIPT:
# {transcript}
# """


# def normalize_report(data, original_text=""):
#     """Return a complete report with stable strings and nullable integer counts."""
#     if not isinstance(data, dict):
#         raise ValueError("Gemini response must be a JSON object.")

#     result = {}
#     for field in TEXT_FIELDS:
#         value = data.get(field)
#         if value is None:
#             result[field] = ""
#         elif isinstance(value, str):
#             result[field] = value.strip()
#         else:
#             logger.warning("Unexpected non-string value for %s: %r", field, value)
#             result[field] = str(value).strip()

#     for field in NUMERIC_FIELDS:
#         value = data.get(field)
#         if value is None or value == "" or isinstance(value, bool):
#             result[field] = None
#         elif isinstance(value, int):
#             result[field] = value if value >= 0 else None
#         elif isinstance(value, float) and value.is_integer() and value >= 0:
#             result[field] = int(value)
#         else:
#             logger.warning("Invalid numeric value for %s: %r", field, value)
#             result[field] = None

#     return result


# def parse_activity_with_gemini(hindi_text):
#     """Translate a Hindi/Hinglish transcript and extract all report fields."""
#     if not isinstance(hindi_text, str) or not hindi_text.strip():
#         raise ValueError("The statement must not be empty.")

#     transcript = hindi_text.strip()
#     prompt = build_prompt(transcript)
#     errors = []

#     for model in AVAILABLE_MODELS:
#         if not model:
#             continue
#         try:
#             logger.info("Trying Gemini model: %s", model)
#             response = client.models.generate_content(
#                 model=model,
#                 contents=prompt,
#                 config=types.GenerateContentConfig(
#                     response_mime_type="application/json",
#                     response_schema=REPORT_SCHEMA,
#                     temperature=0.1,
#                 ),
#             )
#             raw_text = response.text
#             if not raw_text or not raw_text.strip():
#                 raise ValueError("Gemini returned an empty response.")
#             report = normalize_report(json.loads(raw_text.strip()), transcript)
#             logger.info("Successfully extracted report using %s", model)
#             return report
#         except Exception as error:
#             logger.exception("Extraction failed using model %s", model)
#             errors.append(f"{model}: {error}")

#     raise RuntimeError("All configured Gemini models failed. Details: " + " | ".join(errors))

import json
import logging

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

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

# Keep these names aligned with mobile/src/types/report.ts
# and ReportCard.tsx.

TEXT_FIELDS = [
    "worker_name",
    "date",
    "location",
    "organization",
    "village",
    "block",
    "district",
    "activity",
    "issues_identified",
    "education_related_issues",
    "health_and_wellbeing_concerns",
    "family_and_child_welfare_concerns",
    "livelihood_and_financial_issues",
    "government_scheme_and_benefit_issues",
    "elderly_and_disability_support_needs",
    "assistance_provided",
    "actions_taken",
    "referrals_made",
    "services_or_benefits_accessed",
    "referral_required",
    "follow_up_required",
    "follow_up_date",
    "responsible_person",
    "outcomes_and_progress",
    "translated_text",
    "additional_notes",
]

NUMERIC_FIELDS = [
    "people_visited",
    "households_visited",
    "beneficiaries_assisted",
]

ALL_FIELDS = TEXT_FIELDS + NUMERIC_FIELDS

REPORT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        **{
            field: {"type": "STRING"}
            for field in TEXT_FIELDS
        },
        **{
            field: {
                "type": "INTEGER",
                "nullable": True
            }
            for field in NUMERIC_FIELDS
        },
    },
    "required": ALL_FIELDS,
}


def build_prompt(transcript):
    """Extract a complete structured field report from Hindi/Hinglish speech."""

    return f"""
You extract structured reports from social-work field-worker speech in India.

The transcript may be Hindi, Hinglish, or English, and may contain
speech-recognition errors.

Understand the meaning from context but never invent facts.

Return exactly one JSON object matching the supplied schema,
with every required key.

GENERAL RULES:

1. For absent or unclear text fields, return an empty string.
2. For absent or unclear numeric fields, return null.
3. All text values must be in English.
4. Keep names as spoken using sensible English transliteration
   for Hindi names.
5. Prefer YYYY-MM-DD for dates only when the date is unambiguous.
6. Never use today's date to fill a missing activity date.
7. Do not include Markdown or explanations.

EXTRACTION RULES:

- translated_text:
  Provide a faithful, complete English translation of the entire transcript.
  Preserve names, places, numbers, concerns, actions, requests, plans,
  outcomes, and uncertainty.

- worker_name:
  Extract the reporting worker's name only when explicitly stated.
  Do not substitute a speaker ID or the name of a person visited.

- location, village, block, district:
  Extract each geographic level separately only when stated.
  A village/city is not automatically a block or district.
  Location may combine explicitly stated visit-place details
  without adding inferred geography.

- organization:
  Extract explicitly named employer or organization only.

- activity:
  Describe the main work performed concisely.
  Distinguish completed work from intended work.


- households_visited:
  Count households or families visited only when explicitly countable.

- beneficiaries_assisted:
  IMPORTANT: This field requires special attention.

  Count the TOTAL number of DISTINCT PEOPLE who actually received
  help, assistance, support, treatment-related assistance, or services
  from the field worker.

  BENEFICIARY COUNTING RULES:

  1. If the worker explicitly says they helped or assisted a specific
     number of people, use that number as beneficiaries_assisted.

     Examples:
     "चार लोगों की मदद की" = 4
     "पांच लोगों को सहायता दी" = 5
     "तीन लाभार्थियों की मदद की" = 3
     "I helped four people" = 4
     "Assisted six people" = 6

  2. Count ALL people assisted, not just people with specific problems
     or conditions.

  3. Do not reduce the total beneficiary count when the worker
     subsequently mentions a subgroup.

     Example:
     "चार लोगों की मदद की, जिनमें से दो लोग घायल थे"

     Correct:
     beneficiaries_assisted = 4

     Incorrect:
     beneficiaries_assisted = 2

  4. If the worker says they met or visited four people but helped
     only one, then beneficiaries_assisted = 1.

  5. Distinguish between people visited, people discussed, and people
     actually assisted.

     Example:
     "दस लोगों से बातचीत की लेकिन केवल दो लोगों की मदद की"

     beneficiaries_assisted = 2
     people_visited = 10

  6. If the worker explicitly states that assistance was provided
     to a group, count the explicitly stated group size.

  7. Do not count the same person twice when they are mentioned
     in different parts of the transcript.

  8. If a person is mentioned as injured, sick, elderly, or disabled,
     do not automatically assume they were assisted unless the
     transcript indicates that assistance was provided.

  9. If only vague quantities such as "many people" or "several people"
     are mentioned, return null because the schema requires an integer.

  10. If an explicit assistance count is unavailable or unclear,
      return null. Never invent a number.

  BENEFICIARY COUNT EXAMPLES:

  Example 1:
  Transcript: "आज चार लोगों की मदद की।"
  beneficiaries_assisted = 4

  Example 2:
  Transcript: "चार लोगों की मदद की, जिनमें से दो लोग घायल थे।"
  beneficiaries_assisted = 4

  Example 3:
  Transcript: "पांच परिवारों से मिला और तीन लोगों की मदद की।"
  beneficiaries_assisted = 3

  Example 4:
  Transcript: "दस लोगों से बातचीत की लेकिन केवल दो लोगों की मदद की।"
  beneficiaries_assisted = 2

  Example 5:
  Transcript: "कई लोगों की समस्याएं सुनीं।"
  beneficiaries_assisted = null

  Example 6:
  Transcript: "अस्पताल में चार मरीजों की मदद की, जिनमें दो घायल थे।"
  beneficiaries_assisted = 4

- issues_identified:
  Concisely summarize all explicitly stated problems and needs.
  Also put each issue in its matching category below.

- education_related_issues:
  Schooling, attendance, learning, education access, or school needs.

- health_and_wellbeing_concerns:
  Physical or mental health, treatment, nutrition, and wellbeing.

- family_and_child_welfare_concerns:
  Child protection, family safety, caregiving, and family needs.

- livelihood_and_financial_issues:
  Work, income, debt, housing, and basic-needs affordability.

- government_scheme_and_benefit_issues:
  Scheme or benefit applications, eligibility questions, access barriers,
  ration cards, pensions, and other government support.
  Do not infer eligibility.

- elderly_and_disability_support_needs:
  Explicitly stated elderly or disability-related needs.

- assistance_provided:
  Concrete support actually delivered.
  Keep requests and planned support out of this field.

- actions_taken:
  Completed steps taken by the worker, including assessments or contacts.

- referrals_made:
  Referrals that were actually made, with destination if stated.

- services_or_benefits_accessed:
  Services or benefits the person actually obtained or used.

- referral_required:
  Whether a referral is explicitly needed or planned, and where if stated.

- follow_up_required:
  Explicit follow-up need or plan.
  Distinguish this from completed action.

- follow_up_date:
  Date for planned follow-up only, not the activity date.

- responsible_person:
  Explicitly identified person responsible for follow-up or action.

- outcomes_and_progress:
  Explicit results or progress, not predicted results.

- additional_notes:
  Relevant explicit details that do not fit other fields.
  Do not repeat the entire translation here.

IMPORTANT FINAL INSTRUCTIONS:

Do not turn a discussion, request, intention, or need into a completed
action or outcome.

Do not assume that a whole family received help because one member did.

Do not reduce beneficiary totals based on subgroups.

Preserve approximate counts as null if the schema only permits an
integer and no exact count is given.

Keep separate facts in their correct fields.

Before returning the JSON, verify that beneficiaries_assisted reflects
the total explicitly stated number of people who received assistance,
not merely a subgroup of those people.

TRANSCRIPT:

{transcript}
"""


def normalize_report(data, original_text=""):
    """Return a complete report with stable strings and nullable counts."""

    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    result = {}

    for field in TEXT_FIELDS:
        value = data.get(field)

        if value is None:
            result[field] = ""

        elif isinstance(value, str):
            result[field] = value.strip()

        else:
            logger.warning(
                "Unexpected non-string value for %s: %r",
                field,
                value
            )
            result[field] = str(value).strip()

    for field in NUMERIC_FIELDS:
        value = data.get(field)

        if value is None or value == "" or isinstance(value, bool):
            result[field] = None

        elif isinstance(value, int):
            result[field] = value if value >= 0 else None

        elif isinstance(value, float) and value.is_integer() and value >= 0:
            result[field] = int(value)

        else:
            logger.warning(
                "Invalid numeric value for %s: %r",
                field,
                value
            )
            result[field] = None

    return result


def parse_activity_with_gemini(hindi_text):
    """Translate a Hindi/Hinglish transcript and extract all report fields."""

    if not isinstance(hindi_text, str) or not hindi_text.strip():
        raise ValueError("The statement must not be empty.")

    transcript = hindi_text.strip()
    prompt = build_prompt(transcript)

    errors = []

    for model in AVAILABLE_MODELS:

        if not model:
            continue

        try:
            logger.info("Trying Gemini model: %s", model)

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
                raise ValueError("Gemini returned an empty response.")

            report = normalize_report(
                json.loads(raw_text.strip()),
                transcript
            )

            logger.info(
                "Successfully extracted report using %s",
                model
            )

            return report

        except Exception as error:

            logger.exception(
                "Extraction failed using model %s",
                model
            )

            errors.append(f"{model}: {error}")

    raise RuntimeError(
        "All configured Gemini models failed. Details: "
        + " | ".join(errors)
    )
