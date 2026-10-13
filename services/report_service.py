
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

MISSING_VALUES = {
    "",
    "not mentioned",
    "not available",
    "none",
    "null",
    "n/a",
    "na",
}


# ============================================================
# COMMON HELPERS
# ============================================================

def _row_to_dict(log):
    """Convert a SQLite Row or dictionary into a normal dictionary."""
    if isinstance(log, dict):
        return dict(log)

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
    """Display missing or empty values as a dash."""
    value = log.get(key)

    if value is None:
        return "—"

    if isinstance(value, str):
        value = value.strip()

        if value.lower() in MISSING_VALUES:
            return "—"

    return str(value)


def _beneficiary_count(log):
    """Support current and older beneficiary field names."""
    value = log.get("beneficiaries_assisted")

    if value is None or (
        isinstance(value, str)
        and value.strip().lower() in MISSING_VALUES
    ):
        value = log.get("beneficiaries")

    try:
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()

            if value.lower() in MISSING_VALUES:
                return None

        return int(value)

    except (ValueError, TypeError):
        return None


def _safe_filename_date(value):
    """Remove filename-unsafe characters from date strings."""
    return "".join(
        character
        for character in str(value)
        if character.isalnum() or character in "-_"
    )


def _prepare_logs(logs):
    """Normalize database results before generating exports."""
    if not logs:
        return []

    return [_row_to_dict(log) for log in logs]


def _known_numeric_total(logs, key):
    """Sum known numeric values; return None if all values are missing."""
    values = []

    for log in logs:
        value = log.get(key)

        if value is None:
            continue

        if isinstance(value, str):
            value = value.strip()

            if value.lower() in MISSING_VALUES:
                continue

        try:
            values.append(float(value))
        except (ValueError, TypeError):
            continue

    if not values:
        return None

    total = sum(values)

    return int(total) if total.is_integer() else total


def _format_total(value):
    """Format a numeric total or show a dash for missing data."""
    if value is None:
        return "—"

    return str(value)


# ============================================================
# PDF FONT CONFIGURATION — HINDI / UNICODE SUPPORT
# ============================================================

def _configure_pdf_fonts(pdf):
    """
    Register a Unicode font for Hindi, Devanagari, and English.

    Expected font files:
        Noto_Sans_Devanagari/static/NotoSansDevanagari-Regular.ttf
        Noto_Sans_Devanagari/static/NotoSansDevanagari-Bold.ttf

    The services/fonts directory is also supported.

    Install dependencies:
        pip install --upgrade fpdf2 uharfbuzz
    """
    service_dir = Path(__file__).resolve().parent

    font_directories = (
        service_dir / "Noto_Sans_Devanagari" / "static",
        service_dir / "fonts",
    )

    regular_font = None
    bold_font = None

    for font_dir in font_directories:
        candidate_regular = (
            font_dir / "NotoSansDevanagari-Regular.ttf"
        )
        candidate_bold = (
            font_dir / "NotoSansDevanagari-Bold.ttf"
        )
        candidate_simple = (
            font_dir / "NotoSansDevanagari.ttf"
        )

        if candidate_regular.is_file():
            regular_font = candidate_regular
            bold_font = candidate_bold
            break

        if candidate_simple.is_file():
            regular_font = candidate_simple
            bold_font = candidate_simple
            break

    if regular_font is None:
        raise FileNotFoundError(
            "Hindi Unicode font was not found. Place "
            "NotoSansDevanagari-Regular.ttf in "
            f"{service_dir / 'Noto_Sans_Devanagari' / 'static'} "
            "or the services/fonts directory."
        )

    if bold_font is None or not bold_font.is_file():
        bold_font = regular_font

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

    if hasattr(pdf, "set_text_shaping"):
        pdf.set_text_shaping(True)

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
    """Render a label and wrapping value."""
    value = str(value)

    # Start a new page before the field if there is insufficient room.
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
        value,
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(1)


def _pdf_draw_header(pdf, font_name, start_date, end_date):
    """Draw the report header on the current page."""
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
    """Add page numbers to the bottom of every PDF page."""
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
            f"Social Work Field Report | Page {page_number}",
            align="C",
        )


def _pdf_add_new_page(pdf, font_name, start_date, end_date):
    """Add a page and redraw the report header."""
    pdf.add_page()
    _pdf_draw_header(
        pdf,
        font_name,
        start_date,
        end_date,
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

    font_name = _configure_pdf_fonts(pdf)

    # --------------------------------------------------------
    # PAGE 1: REPORT OVERVIEW AND ACTIVITY SUMMARY
    # --------------------------------------------------------

    _pdf_add_new_page(
        pdf,
        font_name,
        start_date,
        end_date,
    )

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

    people_total = _known_numeric_total(
        logs,
        "people_visited",
    )
    household_total = _known_numeric_total(
        logs,
        "households_visited",
    )

    beneficiary_values = [
        _beneficiary_count(log)
        for log in logs
    ]
    beneficiary_values = [
        value
        for value in beneficiary_values
        if value is not None
    ]

    beneficiary_total = (
        sum(beneficiary_values)
        if beneficiary_values
        else None
    )

    metrics = [
        ("ACTIVITY RECORDS", str(len(logs))),
        # ("PEOPLE VISITED", _format_total(people_total)),
        # ("HOUSEHOLDS", _format_total(household_total)),
        (
            "BENEFICIARIES ASSISTED",
            _format_total(beneficiary_total),
        ),
    ]

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

    _pdf_section_heading(
        pdf,
        font_name,
        "Activity Summary",
    )

    for index, log in enumerate(logs, start=1):
        if pdf.get_y() > 245:
            _pdf_add_new_page(
                pdf,
                font_name,
                start_date,
                end_date,
            )

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

        activity_date = _display_value(log, "date")

        if activity_date == "—":
            created_at = _display_value(log, "created_at")
            activity_date = (
                created_at[:10]
                if created_at != "—"
                else "—"
            )

        _pdf_field(
            pdf,
            font_name,
            "Date",
            activity_date,
        )

        _pdf_field(
            pdf,
            font_name,
            "Activity",
            _display_value(log, "activity"),
        )

        beneficiary_count = _beneficiary_count(log)

        _pdf_field(
            pdf,
            font_name,
            "Beneficiaries Assisted",
            (
                str(beneficiary_count)
                if beneficiary_count is not None
                else "—"
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

    _pdf_add_new_page(
        pdf,
        font_name,
        start_date,
        end_date,
    )

    _pdf_section_heading(
        pdf,
        font_name,
        "Detailed Field Visit Records",
    )

    # Only the selected text fields plus supporting metadata.
    fields_to_display = [
        # ("Date", "date"),
        ("Date & Time Recorded", "created_at"),
        ("Worker ID", "speaker_id"),
        ("Social Worker", "worker_name"),
        ("Organization", "organization"),
        ("Location", "location"),
        ("District", "district"),
        ("Activity", "activity"),
        ("Beneficiaries Assisted", "beneficiaries_assisted"),
        ("Original Hindi Statement", "hindi_text"),
        ("Translated Statement", "translated_text"),
        ("Additional Notes", "additional_notes"),
    ]

    for index, log in enumerate(logs, start=1):
        if pdf.get_y() > 245:
            _pdf_add_new_page(
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
            if key == "beneficiaries_assisted":
                count = _beneficiary_count(log)
                value = str(count) if count is not None else "—"
            else:
                value = _display_value(log, key)

            _pdf_field(
                pdf,
                font_name,
                title,
                value,
            )

        photo_file = _value(
            log,
            "photo_file",
            None,
        )

        if photo_file:
            photo_path = PHOTO_DIR / Path(
                str(photo_file)
            ).name

            if photo_path.is_file():
                if pdf.get_y() > 225:
                    _pdf_add_new_page(
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

                pdf.image(
                    str(photo_path),
                    w=100,
                    h=0,
                )

        pdf.ln(7)

    _configure_pdf_page_numbering(
        pdf,
        font_name,
    )

    filename = (
        f"Social_Work_Report_"
        f"{_safe_filename_date(start_date)}"
        f"_to_{_safe_filename_date(end_date)}.pdf"
    )

    output_path = REPORT_DIR / filename
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    people_total = _known_numeric_total(
        logs,
        "people_visited",
    )
    household_total = _known_numeric_total(
        logs,
        "households_visited",
    )

    beneficiary_values = [
        _beneficiary_count(log)
        for log in logs
    ]
    beneficiary_values = [
        value
        for value in beneficiary_values
        if value is not None
    ]

    beneficiary_total = (
        sum(beneficiary_values)
        if beneficiary_values
        else None
    )

    dashboard_metrics = [
        ("Activity Records", len(logs)),
        # ("People Visited", _format_total(people_total)),
        # ("Households Visited", _format_total(household_total)),
        (
            "Beneficiaries Assisted",
            _format_total(beneficiary_total),
        ),
    ]

    summary["A4"] = "REPORTING INDICATOR"
    summary["B4"] = "VALUE"

    for cell in summary[4][:2]:
        cell.font = Font(
            bold=True,
            color="FFFFFF",
        )
        cell.fill = PatternFill(
            "solid",
            fgColor="188985",
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for row_index, (label, value) in enumerate(
        dashboard_metrics,
        start=5,
    ):
        summary.cell(
            row=row_index,
            column=1,
            value=label,
        )
        summary.cell(
            row=row_index,
            column=2,
            value=value,
        )

        summary.cell(
            row=row_index,
            column=1,
        ).font = Font(
            bold=True,
            color="1F3755",
        )

        summary.cell(
            row=row_index,
            column=2,
        ).font = Font(
            bold=True,
            color="188985",
            size=12,
        )

        fill_color = (
            "EDF3F9"
            if row_index % 2
            else "FFFFFF"
        )

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
    # WORKSHEET 2: SELECTED ACTIVITY LOG FIELDS
    # --------------------------------------------------------

    worksheet = workbook.create_sheet("Activity Logs")
    worksheet.sheet_view.showGridLines = False

    headers = [
        "ID",
        "Date & Time Recorded",
        "Worker ID",
        "Worker Name",
        "Organization",
        "Location",
        "District",
        "Original Hindi Statement",
        "Translated Statement",
        "Activity",
        "Beneficiaries Assisted",
        "Additional Notes",
    ]

    worksheet.append(headers)

    for log in logs:
        worksheet.append([
            _value(log, "id", None),
            _value(log, "created_at", None),
            _value(log, "speaker_id", None),
            _display_value(log, "worker_name"),
            _display_value(log, "organization"),
            _display_value(log, "location"),
            _display_value(log, "district"),
            _display_value(log, "hindi_text"),
            _display_value(log, "translated_text"),
            _display_value(log, "activity"),
            _beneficiary_count(log),
            _display_value(log, "additional_notes"),
        ])

    # Header formatting
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

    # Column widths match the 12 selected columns.
    column_widths = {
        1: 9,
        2: 22,
        3: 15,
        4: 22,
        5: 25,
        6: 25,
        7: 20,
        8: 42,
        9: 42,
        10: 36,
        11: 22,
        12: 40,
    }

    for column_index, width in column_widths.items():
        worksheet.column_dimensions[
            get_column_letter(column_index)
        ].width = width

    # Body formatting
    for row_index in range(2, worksheet.max_row + 1):
        worksheet.row_dimensions[row_index].height = 42

        for column_index in range(
            1,
            worksheet.max_column + 1,
        ):
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

            cell.fill = PatternFill(
                "solid",
                fgColor=(
                    "F1F5F9"
                    if row_index % 2 == 0
                    else "FFFFFF"
                ),
            )

    worksheet.freeze_panes = "D2"

    # Add filterable Excel table if records exist.
    if worksheet.max_row >= 2:
        table = Table(
            displayName="SocialWorkActivityLogs",
            ref=(
                f"A1:"
                f"{get_column_letter(worksheet.max_column)}"
                f"{worksheet.max_row}"
            ),
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

    # Page setup for printing
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.page_setup.fitToWidth = 1
    worksheet.page_setup.fitToHeight = 0
    worksheet.page_setup.orientation = "landscape"
    worksheet.sheet_properties.outlinePr.summaryBelow = True

    # --------------------------------------------------------
    # SAVE WORKBOOK
    # --------------------------------------------------------

    filename = (
        f"Social_Work_Logs_"
        f"{_safe_filename_date(start_date)}"
        f"_to_{_safe_filename_date(end_date)}.xlsx"
    )

    output_path = EXPORT_DIR / filename
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    workbook.save(output_path)

    return output_path
