from pathlib import Path

from fpdf import FPDF
from openpyxl import Workbook

from config import EXPORT_DIR, PHOTO_DIR, REPORT_DIR


def generate_pdf(
    logs,
    start_date,
    end_date,
    speaker_id=None
):
    """
    Generate a PDF report from supplied logs.
    """

    if not logs:
        return None

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.add_page()

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    pdf.set_font(
        "Helvetica",
        "B",
        18
    )

    pdf.cell(
        0,
        10,
        "FIELD ACTIVITY REPORT",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C"
    )

    pdf.ln(5)

    # --------------------------------------------------------
    # Information
    # --------------------------------------------------------

    pdf.set_font(
        "Helvetica",
        "",
        11
    )

    pdf.cell(
        0,
        7,
        f"Reporting Period: "
        f"{start_date} to {end_date}",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    if speaker_id:

        pdf.cell(
            0,
            7,
            f"Speaker ID: {speaker_id}",
            new_x="LMARGIN",
            new_y="NEXT"
        )

    pdf.cell(
        0,
        7,
        f"Total Activities: {len(logs)}",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.ln(8)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    pdf.set_font(
        "Helvetica",
        "B",
        14
    )

    pdf.cell(
        0,
        8,
        "Activity Summary",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.ln(2)

    # Header

    pdf.set_font(
        "Helvetica",
        "B",
        8
    )

    pdf.cell(
        25,
        8,
        "Date",
        border=1
    )

    pdf.cell(
        65,
        8,
        "Activity",
        border=1
    )

    pdf.cell(
        45,
        8,
        "Beneficiaries",
        border=1
    )

    pdf.cell(
        55,
        8,
        "Location",
        border=1,
        new_x="LMARGIN",
        new_y="NEXT"
    )

    # Rows

    pdf.set_font(
        "Helvetica",
        "",
        8
    )

    for log in logs:

        date_value = str(
            log["created_at"]
        )[:10]

        activity = str(
            log["activity"]
        )

        beneficiaries = str(
            log["beneficiaries"]
        )

        location = str(
            log["location"]
        )

        pdf.cell(
            25,
            8,
            date_value,
            border=1
        )

        pdf.cell(
            65,
            8,
            activity[:40],
            border=1
        )

        pdf.cell(
            45,
            8,
            beneficiaries[:25],
            border=1
        )

        pdf.cell(
            55,
            8,
            location[:30],
            border=1,
            new_x="LMARGIN",
            new_y="NEXT"
        )

    # --------------------------------------------------------
    # Detailed logs
    # --------------------------------------------------------

    pdf.add_page()

    pdf.set_font(
        "Helvetica",
        "B",
        14
    )

    pdf.cell(
        0,
        8,
        "Detailed Activity Logs",
        new_x="LMARGIN",
        new_y="NEXT"
    )

    pdf.ln(4)

    for index, log in enumerate(
        logs,
        start=1
    ):

        pdf.set_font(
            "Helvetica",
            "B",
            11
        )

        pdf.multi_cell(
            0,
            7,
            text=f"Activity Log {index}",
            new_x="LMARGIN",
            new_y="NEXT"
        )

        fields = [
            (
                "Date & Time",
                log["created_at"]
            ),
            (
                "Speaker",
                log["speaker_id"]
            ),
            (
                "Activity",
                log["activity"]
            ),
            (
                "Beneficiaries",
                log["beneficiaries"]
            ),
            (
                "Location",
                log["location"]
            ),
            (
                "Translated Statement",
                log["translated_text"]
            )
        ]

        for title, value in fields:

            pdf.set_font(
                "Helvetica",
                "B",
                9
            )

            pdf.multi_cell(
                0,
                6,
                text=f"{title}:",
                new_x="LMARGIN",
                new_y="NEXT"
            )

            pdf.set_font(
                "Helvetica",
                "",
                9
            )

            pdf.multi_cell(
                0,
                6,
                text=str(value),
                new_x="LMARGIN",
                new_y="NEXT"
            )

            pdf.ln(1)

        photo_file = log["photo_file"]

        if photo_file:
            photo_path = PHOTO_DIR / Path(photo_file).name

            if photo_path.exists():
                pdf.set_font(
                    "Helvetica",
                    "B",
                    9
                )

                pdf.cell(
                    0,
                    6,
                    "Photo:",
                    new_x="LMARGIN",
                    new_y="NEXT"
                )

                pdf.image(
                    str(photo_path),
                    w=75,
                    h=0
                )

        pdf.ln(4)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    filename = (
        f"Field_Report_"
        f"{start_date.replace('-', '')}_"
        f"to_"
        f"{end_date.replace('-', '')}.pdf"
    )

    output_path = REPORT_DIR / filename

    pdf.output(
        str(output_path)
    )

    return output_path


def generate_excel(
    logs,
    start_date,
    end_date
):
    """
    Generate Excel report from logs.
    """

    if not logs:
        return None

    workbook = Workbook()

    worksheet = workbook.active

    worksheet.title = "Field Activity Logs"

    headers = [
        "ID",
        "Date & Time",
        "Speaker ID",
        "Audio File",
        "Hindi Text",
        "Translated Text",
        "Activity",
        "Beneficiaries",
        "Location"
    ]

    worksheet.append(headers)

    for log in logs:

        worksheet.append([
            log["id"],
            log["created_at"],
            log["speaker_id"],
            log["audio_file"],
            log["hindi_text"],
            log["translated_text"],
            log["activity"],
            log["beneficiaries"],
            log["location"]
        ])

    column_widths = {
        "A": 8,
        "B": 22,
        "C": 15,
        "D": 35,
        "E": 45,
        "F": 45,
        "G": 35,
        "H": 25,
        "I": 25
    }

    for column, width in column_widths.items():

        worksheet.column_dimensions[
            column
        ].width = width

    worksheet.freeze_panes = "A2"

    filename = (
        f"Field_Logs_"
        f"{start_date.replace('-', '')}_"
        f"to_"
        f"{end_date.replace('-', '')}.xlsx"
    )

    output_path = (
        EXPORT_DIR / filename
    )

    workbook.save(
        output_path
    )

    return output_path