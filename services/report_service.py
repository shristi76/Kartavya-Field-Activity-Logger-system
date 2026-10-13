
from pathlib import Path

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Border,
    Side,
    Alignment,
)
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from config import (
    EXPORT_DIR,
    PHOTO_DIR,
    REPORT_DIR,
)


# ============================================================
# REPORT THEME
# ============================================================

NAVY = (31, 55, 85)
TEAL = (24, 137, 133)
LIGHT_BLUE = (237, 243, 249)
LIGHT_TEAL = (230, 245, 242)
DARK_TEXT = (48, 58, 70)
MUTED_TEXT = (105, 117, 130)
WHITE = (255, 255, 255)
BORDER_COLOR = (220, 228, 235)


# ============================================================
# COMMON HELPERS
# ============================================================

def _row_to_dict(log):
    """Convert a SQLite Row or dictionary into a normal dictionary."""
    if isinstance(log, dict):
        return log

    if hasattr(log, "keys"):
        return {key: log[key] for key in log.keys()}

    return dict(log)


def _value(log, key, default=""):
    """Safely retrieve a value from a report."""
    value = log.get(key, default)

    if value is None:
        return default

    return value


def _display_value(log, key):
    """Return a readable value for reports without inventing data."""
    value = _value(log, key, "")

    if isinstance(value, str):
        value = value.strip()

        if not value or value.lower() == "not mentioned":
            return "Not mentioned"

    if value == "":
        return "Not mentioned"

    return str(value)


def _beneficiary_count(log):
    """Support both the current and older beneficiary field names."""
    value = log.get("beneficiaries_assisted")

    if value is None or value == "":
        value = log.get("beneficiaries")

    try:
        return int(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None


def _safe_filename_date(value):
    """Remove filename-unsafe characters from date strings."""
    return "".join(
        character for character in str(value)
        if character.isalnum() or character in "-_"
    )


def _prepare_logs(logs):
    """Normalize database results before generating exports."""
    if not logs:
        return []

    return [_row_to_dict(log) for log in logs]


# ============================================================
# PDF FONT CONFIGURATION
# ============================================================
# ============================================================
# PDF FONT CONFIGURATION — HINDI / UNICODE SUPPORT
# ============================================================

def _configure_pdf_fonts(pdf):
    """
    Register a Unicode font for Hindi, Devanagari, and English text.

    Expected font files:
        Noto_Sans_Devanagari/static/NotoSansDevanagari-Regular.ttf
        Noto_Sans_Devanagari/static/NotoSansDevanagari-Bold.ttf

    The legacy services/fonts directory is also supported.

    The fonts directory should be alongside this Python file.

    Requires:
        pip install --upgrade fpdf2 uharfbuzz

    IMPORTANT:
        This function does not fall back to Helvetica because
        Helvetica cannot render Hindi characters.
    """
    service_dir = Path(__file__).resolve().parent
    font_directories = (
        service_dir / "Noto_Sans_Devanagari" / "static",
        service_dir / "fonts",
    )

    regular_font = None
    bold_font = None

    for font_dir in font_directories:
        candidate_regular = font_dir / "NotoSansDevanagari-Regular.ttf"
        candidate_bold = font_dir / "NotoSansDevanagari-Bold.ttf"
        candidate_simple = font_dir / "NotoSansDevanagari.ttf"

        if candidate_regular.is_file():
            regular_font = candidate_regular
            bold_font = candidate_bold
            break

        if candidate_simple.is_file():
            regular_font = candidate_simple
            bold_font = candidate_simple
            break

    # Stop early with a helpful message if the font is missing.
    if regular_font is None:
        raise FileNotFoundError(
            "Hindi Unicode font was not found. Please place "
            "NotoSansDevanagari-Regular.ttf in "
            f"{service_dir / 'Noto_Sans_Devanagari' / 'static'} "
            "or the legacy services/fonts directory."
        )

    # Use the regular font as a fallback for bold if the
    # separate bold font has not been downloaded.
    if bold_font is None or not bold_font.is_file():
        bold_font = regular_font

    # Register both font styles. Your existing report helpers
    # use pdf.set_font(font_name, 'B', ...) for headings.
    pdf.add_font(
        family="ReportUnicode",
        style="",
        fname=str(regular_font),
    )

    pdf.add_font(
        family="ReportUnicode",
        style="B",
        fname=str(bold_font),
    )

    # Enable Hindi character shaping and ligatures.
    # Install uharfbuzz to support this in fpdf2.
    if hasattr(pdf, "set_text_shaping"):
        pdf.set_text_shaping(True)

    # Set the default font so the PDF starts with Unicode text.
    pdf.set_font("ReportUnicode", size=10)

    return "ReportUnicode"

# ============================================================
# PDF LAYOUT HELPERS
# ============================================================

def _pdf_section_heading(pdf, font_name, title):
    """Draw a consistent colored section heading."""
    if pdf.get_y() > 255:
        pdf.add_page()

    pdf.ln(3)
    pdf.set_fill_color(*LIGHT_BLUE)
    pdf.set_text_color(*NAVY)
    pdf.set_font(font_name, "B", 12)

    pdf.cell(
        0,
        9,
        title,
        border=0,
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(2)
    pdf.set_text_color(*DARK_TEXT)


def _pdf_field(pdf, font_name, label, value):
    """Render a label and a wrapping value without truncating it."""
    value = str(value)

    # Estimate enough room for most fields before rendering.
    # FPDF's automatic page-break handling remains enabled.
    if pdf.get_y() > 250:
        pdf.add_page()

    pdf.set_font(font_name, "B", 9)
    pdf.set_text_color(*NAVY)

    pdf.multi_cell(
        0,
        5,
        f"{label}:",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(*DARK_TEXT)

    pdf.multi_cell(
        0,
        5,
        str(value),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(1)


def _pdf_draw_header(pdf, font_name, start_date, end_date):
    """Draw a consistent report header on the current page."""
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 34, style="F")

    pdf.set_xy(15, 8)
    pdf.set_text_color(*WHITE)
    pdf.set_font(font_name, "B", 16)

    pdf.cell(
        180,
        8,
        "SOCIAL WORK FIELD REPORT",
        align="C",
    )

    pdf.set_xy(15, 20)
    pdf.set_font(font_name, "", 9)

    pdf.cell(
        180,
        6,
        f"Reporting Period: {start_date} to {end_date}",
        align="C",
    )

    pdf.set_y(42)
    pdf.set_text_color(*DARK_TEXT)


def _configure_pdf_page_numbering(pdf, font_name):
    """Add page numbers to the bottom of each PDF page."""
    for page_number in range(1, len(pdf.pages) + 1):
        pdf.page = page_number

        pdf.set_y(-12)
        pdf.set_draw_color(*BORDER_COLOR)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())

        pdf.set_y(-10)
        pdf.set_font(font_name, "", 8)
        pdf.set_text_color(*MUTED_TEXT)

        pdf.cell(
            0,
            5,
            f"Social Work Field Report  |  Page {page_number}",
            align="C",
        )


# ============================================================
# PDF EXPORT
# ============================================================

def generate_pdf(
    logs,
    start_date,
    end_date,
    speaker_id=None,
):
    """Generate a professionally formatted social-work PDF."""
    logs = _prepare_logs(logs)

    if not logs:
        return None

    pdf = FPDF(format="A4")
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=18)

    # Use a Unicode font when available.
    font_name = _configure_pdf_fonts(pdf)

    # --------------------------------------------------------
    # PAGE 1: REPORT COVER AND ACTIVITY SUMMARY
    # --------------------------------------------------------

    pdf.add_page()
    _pdf_draw_header(pdf, font_name, start_date, end_date)

    pdf.set_font(font_name, "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(
        0,
        9,
        "Reporting Overview",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(*DARK_TEXT)

    pdf.cell(
        0,
        7,
        f"Total activity records: {len(logs)}",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    if speaker_id:
        pdf.cell(
            0,
            7,
            f"Worker ID: {speaker_id}",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(5)

    # Summary metrics are calculated from the available records.
    # Missing counts are excluded instead of being treated as zero.
    people_values = []
    household_values = []
    beneficiary_values = []

    for log in logs:
        for key, target in [
            ("people_visited", people_values),
            ("households_visited", household_values),
        ]:
            value = log.get(key)

            try:
                if value not in (None, ""):
                    target.append(float(value))
            except (ValueError, TypeError):
                pass

        beneficiaries = _beneficiary_count(log)

        if beneficiaries is not None:
            beneficiary_values.append(beneficiaries)

    metrics = [
        (
            "ACTIVITY RECORDS",
            str(len(logs)),
        ),
        (
            "PEOPLE VISITED",
            str(int(sum(people_values)))
            if people_values else "Not available",
        ),
        (
            "HOUSEHOLDS",
            str(int(sum(household_values)))
            if household_values else "Not available",
        ),
        (
            "BENEFICIARIES ASSISTED",
            str(sum(beneficiary_values))
            if beneficiary_values else "Not available",
        ),
    ]

    # Draw four summary cards.
    card_gap = 4
    card_width = (180 - card_gap * 3) / 4
    card_height = 24
    card_y = pdf.get_y()

    for index, (label, value) in enumerate(metrics):
        card_x = 15 + index * (card_width + card_gap)

        pdf.set_fill_color(*LIGHT_BLUE)
        pdf.set_draw_color(*BORDER_COLOR)

        pdf.rect(
            card_x,
            card_y,
            card_width,
            card_height,
            style="DF",
        )

        pdf.set_xy(card_x + 1, card_y + 4)
        pdf.set_font(font_name, "B", 10)
        pdf.set_text_color(*NAVY)

        pdf.cell(
            card_width - 2,
            6,
            value[:24],
            align="C",
        )

        pdf.set_xy(card_x + 1, card_y + 12)
        pdf.set_font(font_name, "", 6.5)
        pdf.set_text_color(*MUTED_TEXT)

        pdf.multi_cell(
            card_width - 2,
            4,
            label,
            align="C",
        )

    pdf.set_y(card_y + card_height + 10)

    # Activity summary. Each record wraps over multiple lines,
    # so longer activities and locations are not cut off.
    _pdf_section_heading(
        pdf,
        font_name,
        "Activity Summary",
    )

    for index, log in enumerate(logs, start=1):
        pdf.set_fill_color(*LIGHT_TEAL)

        pdf.set_font(font_name, "B", 10)
        pdf.set_text_color(*NAVY)

        pdf.cell(
            0,
            8,
            f"Activity {index}",
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )

        _pdf_field(
            pdf,
            font_name,
            "Date",
            _display_value(log, "date")
            if log.get("date")
            else str(_value(log, "created_at", "Not mentioned"))[:10],
        )

        _pdf_field(
            pdf,
            font_name,
            "Activity",
            _display_value(log, "activity"),
        )

        _pdf_field(
            pdf,
            font_name,
            "Beneficiaries Assisted",
            (
                str(_beneficiary_count(log))
                if _beneficiary_count(log) is not None
                else "Not mentioned"
            ),
        )

        _pdf_field(
            pdf,
            font_name,
            "Location",
            _display_value(log, "location"),
        )

        pdf.ln(3)

    # --------------------------------------------------------
    # DETAILED FIELD VISIT RECORDS
    # --------------------------------------------------------

    pdf.add_page()
    _pdf_draw_header(pdf, font_name, start_date, end_date)

    _pdf_section_heading(
        pdf,
        font_name,
        "Detailed Field Visit Records",
    )

    fields_to_display = [
        ("Date", "date"),
        ("Date & Time Recorded", "created_at"),
        ("Worker ID", "speaker_id"),
        ("Social Worker", "worker_name"),
        ("Organization", "organization"),
        ("Location", "location"),
        ("Village", "village"),
        ("Block", "block"),
        ("District", "district"),
        ("Activity", "activity"),
        ("People Visited", "people_visited"),
        ("Households Visited", "households_visited"),
        ("Beneficiaries Assisted", "beneficiaries_assisted"),
        ("Issues Identified", "issues_identified"),
        ("Education-Related Issues", "education_related_issues"),
        ("Health and Wellbeing Concerns", "health_and_wellbeing_concerns"),
        ("Family and Child Welfare Concerns", "family_and_child_welfare_concerns"),
        ("Livelihood and Financial Issues", "livelihood_and_financial_issues"),
        ("Government Scheme and Benefit Issues", "government_scheme_and_benefit_issues"),
        ("Elderly and Disability Support Needs", "elderly_and_disability_support_needs"),
        ("Assistance Provided", "assistance_provided"),
        ("Actions Taken", "actions_taken"),
        ("Referrals Made", "referrals_made"),
        ("Services or Benefits Accessed", "services_or_benefits_accessed"),
        ("Referral Required", "referral_required"),
        ("Follow-Up Required", "follow_up_required"),
        ("Follow-Up Date", "follow_up_date"),
        ("Responsible Person", "responsible_person"),
        ("Outcomes and Progress", "outcomes_and_progress"),
        ("Original Statement", "hindi_text"),
        ("Translated Statement", "translated_text"),
        ("Additional Notes", "additional_notes"),
    ]

    for index, log in enumerate(logs, start=1):
        if pdf.get_y() > 245:
            pdf.add_page()
            _pdf_draw_header(
                pdf,
                font_name,
                start_date,
                end_date,
            )

        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(*WHITE)
        pdf.set_font(font_name, "B", 11)

        pdf.cell(
            0,
            9,
            f"FIELD VISIT {index}",
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.set_text_color(*DARK_TEXT)
        pdf.ln(2)

        for title, key in fields_to_display:
            # Support old records that stored beneficiaries
            # under the original field name.
            if key == "beneficiaries_assisted":
                beneficiary_count = _beneficiary_count(log)

                value = (
                    str(beneficiary_count)
                    if beneficiary_count is not None
                    else "Not mentioned"
                )
            else:
                value = _display_value(log, key)

            _pdf_field(
                pdf,
                font_name,
                title,
                value,
            )

        # Include an associated photo, if one exists.
        photo_file = _value(log, "photo_file", None)

        if photo_file:
            photo_path = PHOTO_DIR / Path(str(photo_file)).name

            if photo_path.is_file():
                if pdf.get_y() > 225:
                    pdf.add_page()
                    _pdf_draw_header(
                        pdf,
                        font_name,
                        start_date,
                        end_date,
                    )

                pdf.ln(3)

                pdf.set_font(font_name, "B", 10)
                pdf.set_text_color(*NAVY)

                pdf.cell(
                    0,
                    7,
                    "Visit Photo",
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

                # Keep images within the printable page width.
                pdf.image(
                    str(photo_path),
                    w=100,
                    h=0,
                )

        pdf.ln(7)

    # Add a consistent footer to every page.
    _configure_pdf_page_numbering(pdf, font_name)

    filename = (
        f"Social_Work_Report_{_safe_filename_date(start_date)}"
        f"_to_{_safe_filename_date(end_date)}.pdf"
    )

    output_path = REPORT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf.output(str(output_path))
    return output_path


# ============================================================
# EXCEL EXPORT
# ============================================================

def generate_excel(
    logs,
    start_date,
    end_date,
):
    """Generate a styled Excel workbook with a summary dashboard."""
    logs = _prepare_logs(logs)

    if not logs:
        return None

    workbook = Workbook()

    # --------------------------------------------------------
    # WORKSHEET 1: SUMMARY DASHBOARD
    # --------------------------------------------------------

    summary = workbook.active
    summary.title = "Summary"

    summary.sheet_view.showGridLines = False

    summary.merge_cells("A1:D1")
    summary["A1"] = "SOCIAL WORK FIELD REPORT"

    summary["A1"].font = Font(
        name="Aptos Display",
        size=18,
        bold=True,
        color="FFFFFF",
    )
    summary["A1"].fill = PatternFill(
        "solid",
        fgColor="1F3755",
    )
    summary["A1"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )
    summary.row_dimensions[1].height = 38

    summary.merge_cells("A2:D2")
    summary["A2"] = (
        f"Reporting Period: {start_date} to {end_date}"
    )
    summary["A2"].font = Font(
        size=11,
        italic=True,
        color="506176",
    )
    summary["A2"].alignment = Alignment(
        horizontal="center",
        vertical="center",
    )
    summary.row_dimensions[2].height = 25

    people_total = 0
    household_total = 0
    beneficiary_total = 0

    people_known = False
    households_known = False
    beneficiaries_known = False

    for log in logs:
        try:
            value = log.get("people_visited")

            if value not in (None, ""):
                people_total += float(value)
                people_known = True
        except (ValueError, TypeError):
            pass

        try:
            value = log.get("households_visited")

            if value not in (None, ""):
                household_total += float(value)
                households_known = True
        except (ValueError, TypeError):
            pass

        beneficiary_count = _beneficiary_count(log)

        if beneficiary_count is not None:
            beneficiary_total += beneficiary_count
            beneficiaries_known = True

    dashboard_metrics = [
        ("Activity Records", len(logs)),
        (
            "People Visited",
            int(people_total) if people_known else "Not available",
        ),
        (
            "Households Visited",
            int(household_total) if households_known else "Not available",
        ),
        (
            "Beneficiaries Assisted",
            beneficiary_total if beneficiaries_known else "Not available",
        ),
    ]

    summary["A4"] = "REPORTING INDICATOR"
    summary["B4"] = "VALUE"

    for cell in summary[4][:2]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="188985")
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for row_index, (label, value) in enumerate(
        dashboard_metrics,
        start=5,
    ):
        summary.cell(row=row_index, column=1, value=label)
        summary.cell(row=row_index, column=2, value=value)

        summary.cell(row=row_index, column=1).font = Font(
            bold=True,
            color="1F3755",
        )
        summary.cell(row=row_index, column=2).font = Font(
            bold=True,
            color="188985",
            size=12,
        )

        fill_color = "EDF3F9" if row_index % 2 else "FFFFFF"

        for column_index in (1, 2):
            cell = summary.cell(
                row=row_index,
                column=column_index,
            )
            cell.fill = PatternFill(
                "solid",
                fgColor=fill_color,
            )
            cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
            )
            cell.border = Border(
                bottom=Side(
                    style="thin",
                    color="DCE4EB",
                )
            )

        summary.row_dimensions[row_index].height = 25

    summary.column_dimensions["A"].width = 32
    summary.column_dimensions["B"].width = 25
    summary.column_dimensions["C"].width = 18
    summary.column_dimensions["D"].width = 18

    summary.freeze_panes = "A4"

    # --------------------------------------------------------
    # WORKSHEET 2: DETAILED ACTIVITY LOGS
    # --------------------------------------------------------

    worksheet = workbook.create_sheet("Activity Logs")
    worksheet.sheet_view.showGridLines = False

    headers = [
        "ID",
        "Date & Time",
        "Worker ID",
        "Worker Name",
        "Organization",
        "Audio File",
        "Original Statement",
        "Translated Statement",
        "Activity",
        "People Visited",
        "Households Visited",
        "Beneficiaries Assisted",
        "Location",
        "Village",
        "Block",
        "District",
        "Issues Identified",
        "Education-Related Issues",
        "Health and Wellbeing Concerns",
        "Family and Child Welfare Concerns",
        "Livelihood and Financial Issues",
        "Government Scheme and Benefit Issues",
        "Elderly and Disability Support Needs",
        "Assistance Provided",
        "Actions Taken",
        "Referrals Made",
        "Services or Benefits Accessed",
        "Referral Required",
        "Follow-Up Required",
        "Follow-Up Date",
        "Responsible Person",
        "Outcomes and Progress",
        "Additional Notes",
    ]

    worksheet.append(headers)

    for log in logs:
        worksheet.append([
            _value(log, "id", None),
            _value(log, "created_at", None),
            _value(log, "speaker_id", None),
            _value(log, "worker_name", None),
            _value(log, "organization", None),
            _value(log, "audio_file", None),
            _value(log, "hindi_text", None),
            _value(log, "translated_text", None),
            _value(log, "activity", None),
            _value(log, "people_visited", None),
            _value(log, "households_visited", None),
            _beneficiary_count(log),
            _value(log, "location", None),
            _value(log, "village", None),
            _value(log, "block", None),
            _value(log, "district", None),
            _value(log, "issues_identified", None),
            _value(log, "education_related_issues", None),
            _value(log, "health_and_wellbeing_concerns", None),
            _value(log, "family_and_child_welfare_concerns", None),
            _value(log, "livelihood_and_financial_issues", None),
            _value(log, "government_scheme_and_benefit_issues", None),
            _value(log, "elderly_and_disability_support_needs", None),
            _value(log, "assistance_provided", None),
            _value(log, "actions_taken", None),
            _value(log, "referrals_made", None),
            _value(log, "services_or_benefits_accessed", None),
            _value(log, "referral_required", None),
            _value(log, "follow_up_required", None),
            _value(log, "follow_up_date", None),
            _value(log, "responsible_person", None),
            _value(log, "outcomes_and_progress", None),
            _value(log, "additional_notes", None),
        ])

    # Styled column header.
    for cell in worksheet[1]:
        cell.font = Font(
            name="Aptos",
            bold=True,
            color="FFFFFF",
            size=10,
        )
        cell.fill = PatternFill(
            "solid",
            fgColor="1F3755",
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        cell.border = Border(
            bottom=Side(
                style="medium",
                color="188985",
            )
        )

    worksheet.row_dimensions[1].height = 42

    # Column widths match the actual 33 exported columns.
    column_widths = {
        1: 9,
        2: 22,
        3: 15,
        4: 22,
        5: 25,
        6: 28,
        7: 42,
        8: 42,
        9: 36,
        10: 16,
        11: 18,
        12: 22,
        13: 25,
        14: 22,
        15: 18,
        16: 20,
        17: 40,
        18: 35,
        19: 35,
        20: 40,
        21: 35,
        22: 40,
        23: 40,
        24: 35,
        25: 35,
        26: 30,
        27: 35,
        28: 20,
        29: 20,
        30: 20,
        31: 25,
        32: 35,
        33: 40,
    }

    for column_index, width in column_widths.items():
        worksheet.column_dimensions[
            get_column_letter(column_index)
        ].width = width

    # Format all data rows for readability.
    for row_index in range(2, worksheet.max_row + 1):
        worksheet.row_dimensions[row_index].height = 42

        for column_index in range(1, worksheet.max_column + 1):
            cell = worksheet.cell(
                row=row_index,
                column=column_index,
            )

            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

            cell.border = Border(
                bottom=Side(
                    style="hair",
                    color="DCE4EB",
                )
            )

            # Alternating row fills make large datasets easier to scan.
            if row_index % 2 == 0:
                cell.fill = PatternFill(
                    "solid",
                    fgColor="F1F5F9",
                )
            else:
                cell.fill = PatternFill(
                    "solid",
                    fgColor="FFFFFF",
                )

    # Freeze the headings and first three identifying columns.
    worksheet.freeze_panes = "D2"

    # Enable native Excel filtering and table styling.
    if worksheet.max_row >= 2:
        table = Table(
            displayName="SocialWorkActivityLogs",
            ref=f"A1:{get_column_letter(worksheet.max_column)}"
                f"{worksheet.max_row}",
        )

        table_style = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )

        table.tableStyleInfo = table_style
        worksheet.add_table(table)

    # Keep workbook calculation and viewing behavior convenient.
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.page_setup.orientation = "landscape"
    worksheet.sheet_properties.outlinePr.summaryBelow = True

    # --------------------------------------------------------
    # SAVE WORKBOOK
    # --------------------------------------------------------

    filename = (
        f"Social_Work_Logs_{_safe_filename_date(start_date)}"
        f"_to_{_safe_filename_date(end_date)}.xlsx"
    )

    output_path = EXPORT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    workbook.save(output_path)

    return output_path
