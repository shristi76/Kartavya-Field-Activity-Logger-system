
import json
import logging
from datetime import date, datetime, timedelta

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)

AVAILABLE_MODELS = list(dict.fromkeys([
    GEMINI_MODEL,
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]))

NUMERIC_FIELDS = {
    "people_visited",
    "households_visited",
    "beneficiaries_assisted",
}

TEXT_FIELDS = [
    "worker_name",
    "date",
    "location",
    "organization",
    "village",
    "block",
    "district",
    "translated_text",
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
    "additional_notes",
]

ALL_FIELDS = TEXT_FIELDS + list(NUMERIC_FIELDS)


# --------------------------------------------------
# JSON SCHEMA
# --------------------------------------------------

REPORT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        field: {"type": "INTEGER", "nullable": True}
        for field in NUMERIC_FIELDS
    } | {
        field: {"type": "STRING"}
        for field in TEXT_FIELDS
    },
    "required": ALL_FIELDS,
}


# --------------------------------------------------
# PROMPT
# --------------------------------------------------

def build_prompt(hindi_text):
    return f"""
You are an expert AI assistant for a social-work field
reporting system in India.

Your task is to understand the COMPLETE statement spoken
by a community worker in Hindi, Hinglish, or English and
extract accurate information into the required JSON fields.

Return ONLY a JSON object matching the supplied schema.

GENERAL RULES:
1. Understand natural spoken Hindi, Hinglish, synonyms,
   common speech patterns, and social-work terminology.
2. Translate the complete statement faithfully into English
   in the translated_text field.
3. Do not invent or guess information.
4. For missing text fields, return an empty string "".
5. For missing numeric fields, return null.
6. Numeric fields must contain integers or null, never strings.
7. Preserve names, dates, quantities, locations, and details.
8. Do not omit an issue merely because it belongs to more
   than one relevant category.
9. Separate completed actions from planned actions.
10. Do not claim that a referral, service, benefit, or
    resolution occurred unless explicitly supported.
11. Do not infer eligibility for government schemes.
12. Preserve uncertainty instead of guessing.
13. Use respectful, neutral language.
14. Do not put phrases such as "Not mentioned", "N/A",
    or "Unknown" in missing text fields. Use "" instead.
15. Do not change facts in order to fill every field.

FIELD-BY-FIELD RULES:

worker_name:
The name of the reporting worker, if spoken.

date:
The date of the reported activity. Prefer YYYY-MM-DD.
Use the explicitly stated date. Do not silently substitute
the current date.

location:
The general location of the activity, including any
location detail explicitly stated.

organization:
The name of the worker's organization, if stated.

village:
The village name only. Do not copy a district name here.

block:
The block name only, if explicitly stated.

district:
The district name only, if explicitly stated.

translated_text:
A faithful English translation of the entire original
statement. Preserve important details and intentions.

activity:
A short description of the main activity, such as
community survey, household visits, counselling, or
identification of welfare issues.

people_visited:
The number of individual people visited or spoken to.
For example, "बारह लोगों से बातचीत की" means 12.
Do not substitute the number of households or cases.

households_visited:
The number of households or families visited.
For example, "आठ परिवारों से मुलाकात की" means 8.

beneficiaries_assisted:
The number of distinct people explicitly stated to have
received assistance. Do not count everyone visited,
everyone with a problem, or everyone interviewed.
If the count cannot be established, return null.

issues_identified:
Summarize every problem explicitly reported or observed.

education_related_issues:
Only education, school attendance, educational access,
or school-related concerns.

health_and_wellbeing_concerns:
Health, healthcare access, physical wellbeing, or
mental wellbeing concerns explicitly stated.

family_and_child_welfare_concerns:
Child protection, family welfare, neglect, or child-related
concerns explicitly stated.

livelihood_and_financial_issues:
Employment, livelihood, income, debt, or financial
difficulties explicitly stated. Do not infer poverty merely
because a benefit has not been received.

government_scheme_and_benefit_issues:
Problems related to ration cards, pensions, government
schemes, benefit applications, or benefit delivery.
Include the number of affected families when stated.

elderly_and_disability_support_needs:
Explicitly stated elderly-care or disability-related needs.
A pension problem may be included here if the statement
identifies the person as elderly or identifies elderly care.
Do not infer a disability.

assistance_provided:
Help actually provided by the worker. Recording a complaint
is an action, but does not mean the underlying problem
has been resolved or financial assistance was provided.

actions_taken:
Actions completed, such as visiting families, interviewing
people, documenting problems, or contacting an official.
Keep planned actions clearly labelled as planned.

referrals_made:
Referrals already completed to an officer, service,
hospital, or organization. A plan to contact an officer
is not a completed referral.

services_or_benefits_accessed:
Services or benefits explicitly received or accessed.
A requested or delayed benefit is not an accessed benefit.

referral_required:
Use "Yes" if a referral is explicitly required or clearly
indicated. If unclear, return "".
Do not state that a referral has already been completed
when only a future contact is planned.

follow_up_required:
Use "Yes" if another visit, check, or review is planned.
Otherwise use "No" only if the statement explicitly
indicates that follow-up is unnecessary. If unclear, use "".

follow_up_date:
The explicitly stated follow-up date. Resolve relative dates
only when the reference date is clear.
If "next Monday" is stated and the activity date is
2026-10-13, the follow-up date is 2026-10-19.

responsible_person:
The person explicitly identified as responsible for follow-up.
If the worker says "I will revisit", use the worker's name
when available.

outcomes_and_progress:
Report confirmed outcomes and progress. If issues remain
unresolved or the outcome is not yet known, say so accurately.

additional_notes:
Relevant information not captured elsewhere, including
ambiguity and details that require verification.

CLASSIFICATION EXAMPLE:

Input:
"मेरा नाम सुनीता देवी है। मैं 13 अक्टूबर 2026 को पटना
जिले के एक गाँव में गई। मैंने आठ परिवारों से मुलाकात की
और बारह लोगों से बातचीत की। तीन परिवारों ने राशन कार्ड
की समस्या बताई और एक परिवार को वृद्धावस्था पेंशन नहीं
मिल रही है। मैंने समस्याएँ दर्ज कीं और पंचायत अधिकारी
से संपर्क करने की योजना बनाई। मैं अगले सोमवार फिर जाऊँगी।"

Expected interpretation:
- worker_name: Sunita Devi
- date: 2026-10-13
- district: Patna
- people_visited: 12
- households_visited: 8
- beneficiaries_assisted: null, unless assistance recipients
  are explicitly identified and counted
- issues_identified: ration card problems affecting three
  families and a pension problem affecting one family
- government_scheme_and_benefit_issues: include both issues
- assistance_provided: document the problems, without
  claiming that the benefits were delivered
- actions_taken: visited families, spoke with people, and
  recorded their problems
- referrals_made: empty because contact is only planned
- referral_required: Yes if the planned official contact
  clearly indicates a referral is needed
- follow_up_required: Yes
- follow_up_date: 2026-10-19
- responsible_person: Sunita Devi
- outcomes_and_progress: resolution has not yet been confirmed

Do not copy this example's values unless supported by the
actual input statement.

STATEMENT TO PROCESS:
{hindi_text}
"""


# --------------------------------------------------
# NORMALIZE AND VALIDATE GEMINI RESPONSE
# --------------------------------------------------

def normalize_report(data, original_text):
    if not isinstance(data, dict):
        raise ValueError("Gemini response must be a JSON object.")

    result = {}

    for field in ALL_FIELDS:
        value = data.get(field)

        if field in NUMERIC_FIELDS:
            if value is None or value == "":
                result[field] = None
            elif isinstance(value, bool):
                result[field] = None
            elif isinstance(value, int):
                result[field] = value
            elif isinstance(value, float) and value.is_integer():
                result[field] = int(value)
            else:
                # Do not silently convert unexpected values
                # into a potentially incorrect count.
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
                result[field] = str(value).strip()

    # Keep the original statement available in case the
    # caller needs to compare or audit the extraction.
    result["translated_text"] = result["translated_text"].strip()

    return result


# --------------------------------------------------
# MAIN EXTRACTION FUNCTION
# --------------------------------------------------

def parse_activity_with_gemini(hindi_text):
    """
    Translate a Hindi/Hinglish statement and extract
    structured social-work report fields.

    Returns a dictionary containing the fixed report schema.
    Raises RuntimeError if all configured models fail.
    """

    if not isinstance(hindi_text, str) or not hindi_text.strip():
        raise ValueError("The Hindi statement must not be empty.")

    prompt = build_prompt(hindi_text.strip())
    errors = []

    for model in AVAILABLE_MODELS:
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

            # Structured output should already be JSON.
            # json.loads still validates the returned content.
            data = json.loads(raw_text.strip())

            report = normalize_report(data, hindi_text)

            logger.info(
                "Successfully extracted report using %s",
                model,
            )

            return report

        except Exception as error:
            logger.exception(
                "Gemini extraction failed with model %s",
                model,
            )
            errors.append(f"{model}: {error}")

    raise RuntimeError(
        "All configured Gemini models failed. Details: "
        + " | ".join(errors)
    )
