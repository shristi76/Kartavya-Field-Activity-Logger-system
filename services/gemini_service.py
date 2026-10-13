
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
    Understand Hindi/Hinglish field-worker speech
    and convert it into structured social-work data.
    """

    prompt = f"""
You are an AI assistant for a social
field-worker reporting system.

A social worker or community field worker speaks
naturally in Hindi, Hinglish, or a mixture of
Hindi and English.

The worker may describe household visits, beneficiary
interactions, family circumstances, education,
child welfare, elderly care, disability support,
government welfare schemes, community development,
livelihood challenges, referrals, services provided,
and follow-up activities.

Your job is to understand the COMPLETE statement
and extract every useful piece of information relevant
to social work.

IMPORTANT RULES:

1. Understand natural spoken Hindi.
2. Understand Hinglish and common social-work terminology.
3. Translate the complete statement into clear English.
4. Do NOT invent information.
5. Do NOT guess missing information.
6. If a field is not mentioned, return "Not mentioned".
7. Keep all numbers accurate.
8. Convert spoken numbers into numeric values where appropriate.
9. Preserve beneficiary information and reported circumstances accurately.
10. Understand different ways of saying the same thing.
11. "बीस परिवार", "20 परिवार", and "20 families" all mean 20 families.
12. "पांच बच्चों को स्कूल जाने में समस्या है" means 5 children are facing difficulties attending school.
13. "तीन परिवारों को सरकारी योजना का लाभ नहीं मिला" means 3 families have not received the benefits of a government scheme.
14. "वृद्ध व्यक्ति को पेंशन नहीं मिल रही है" means an elderly person is not receiving a pension.
15. "अगले सप्ताह फिर से मिलने जाना है" means a follow-up visit is planned for next week.
16. Do not create information that was not spoken.
17. If the worker's name is mentioned, extract it.
18. If a location is mentioned, extract it.
19. If a village, block, district, organization, or community center is mentioned, preserve it.
20. Extract all important social observations and beneficiary needs.
21. Extract assistance provided, actions taken, referrals,
    unresolved concerns, and follow-up information if mentioned.
22. Identify the number of people or households visited
    only when the statement provides enough information.
23. Do not confuse the number of people visited with the
    number of people experiencing a particular problem.
24. Distinguish between information reported by a beneficiary,
    observations made by the worker, and actions actually completed.
25. Do not claim that a government benefit, service, or referral
    was completed unless the worker explicitly says so.
26. Do not infer a person's eligibility for a government scheme.
27. Preserve names, dates, quantities, locations, and scheme names
    as accurately as possible.
28. If a date is not explicitly provided, do not assume today's date.
29. If a field is not relevant to the described activity,
    return "Not mentioned".
30. Use respectful, neutral, non-judgmental language.
31. Protect sensitive beneficiary information. Do not infer
    personal characteristics or sensitive circumstances.
32. If the statement contains multiple activities or concerns,
    capture all of them without omitting important details.
33. Keep translated_text as a faithful English translation
    of the worker's complete statement.
34. Keep activity as a concise description of the main
    social-work activity performed or reported.
35. For numeric fields, return a JSON number when explicitly
    stated or unambiguously supported by the statement.
    If the number is unknown or not stated, return null.
36. Do not interpret a planned action as a completed action.
37. If information is ambiguous or contradictory, preserve
    the uncertainty in additional_notes instead of guessing.

Return ONLY valid JSON.
Do not include Markdown, explanations, or text outside the JSON.

Use EXACTLY this structure:

{{
    "worker_name": "",
    "date": "",
    "location": "",
    "organization": "",
    "village": "",
    "block": "",
    "district": "",

    "translated_text": "",

    "activity": "",

    "people_visited": null,
    "households_visited": null,
    "beneficiaries_assisted": null,

    "issues_identified": "",
    "education_related_issues": "",
    "health_and_wellbeing_concerns": "",
    "family_and_child_welfare_concerns": "",
    "livelihood_and_financial_issues": "",
    "government_scheme_and_benefit_issues": "",
    "elderly_and_disability_support_needs": "",

    "assistance_provided": "",
    "actions_taken": "",
    "referrals_made": "",
    "services_or_benefits_accessed": "",
    "referral_required": "",

    "follow_up_required": "",
    "follow_up_date": "",
    "responsible_person": "",

    "outcomes_and_progress": "",
    "additional_notes": ""
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

        if response is None:

            raise RuntimeError(
                f"All Gemini models failed: {last_error}"
            )

        if not response.text:

            raise RuntimeError(
                "Gemini returned no text."
            )

        raw_text = response.text.strip()

        # Remove markdown JSON fences if Gemini adds them
        if raw_text.startswith("```json"):

            raw_text = raw_text[7:]

        elif raw_text.startswith("```"):

            raw_text = raw_text[3:]

        if raw_text.endswith("```"):

            raw_text = raw_text[:-3]

        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        required_fields = [
            "worker_name",
            "date",
            "location",
            "organization",
            "village",
            "block",
            "district",
            "translated_text",
            "activity",
            "people_visited",
            "households_visited",
            "beneficiaries_assisted",
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
            "additional_notes"
        ]

        for field in required_fields:

            if field not in data:

                data[field] = "Not mentioned"

            if data[field] is None:

                if field in [
                    "people_visited",
                    "households_visited",
                    "beneficiaries_assisted"
                ]:
                    data[field] = None

                else:
                    data[field] = "Not mentioned"

        return data

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"Gemini returned invalid JSON: {error}"
        )

    except Exception as error:

        raise RuntimeError(
            f"Gemini processing failed: {error}"
        )
