from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_payslip_pdf(
    employee_name: str,
    employee_code: str,
    department: Optional[str],
    position: Optional[str],
    period_month: int,
    period_year: int,
    gross_salary: float,
    total_allowances: float,
    total_ot_amount: float,
    gross_income: float,
    personal_deduction: float,
    dependent_deduction: float,
    taxable_income: float,
    income_tax: float,
    insurance_premium: float,
    net_salary: float,
    work_days: float,
    actual_work_days: float,
) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=5,
    )
    normal_style = styles["Normal"]

    story = []

    story.append(Paragraph("PHIẾU LƯƠNG", title_style))
    story.append(
        Paragraph(
            f"Tháng {period_month} / {period_year}",
            ParagraphStyle("Period", fontSize=12, alignment=1, spaceAfter=20),
        )
    )

    story.append(Paragraph("THÔNG TIN NHÂN VIÊN", heading_style))
    info_data = [
        ["Mã NV:", employee_code],
        ["Họ tên:", employee_name],
        ["Phòng ban:", department or "N/A"],
        ["Chức vụ:", position or "N/A"],
    ]
    info_table = Table(info_data, colWidths=[1.5 * inch, 4 * inch])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("CHI TIẾT LƯƠNG", heading_style))
    salary_data = [
        ["Lương gross:", f"{gross_salary:,.0f} VNĐ"],
        ["Phụ cấp:", f"{total_allowances:,.0f} VNĐ"],
        ["Tiền OT:", f"{total_ot_amount:,.0f} VNĐ"],
        ["Tổng thu nhập:", f"{gross_income:,.0f} VNĐ"],
    ]
    salary_table = Table(salary_data, colWidths=[3 * inch, 2.5 * inch])
    salary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    story.append(salary_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("KHẤU TRỪ", heading_style))
    deduction_data = [
        ["Giảm trừ cá nhân:", f"{personal_deduction:,.0f} VNĐ"],
        ["Giảm trừ người phụ thuộc:", f"{dependent_deduction:,.0f} VNĐ"],
        ["Thuế TNCN:", f"{income_tax:,.0f} VNĐ"],
        ["BHXH, BHYT, BHTN:", f"{insurance_premium:,.0f} VNĐ"],
    ]
    deduction_table = Table(deduction_data, colWidths=[3 * inch, 2.5 * inch])
    deduction_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(deduction_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("CÔNG VIỆC", heading_style))
    work_data = [
        ["Ngày công chuẩn:", f"{work_days:.1f}"],
        ["Ngày công thực tế:", f"{actual_work_days:.1f}"],
    ]
    work_table = Table(work_data, colWidths=[3 * inch, 2.5 * inch])
    work_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(work_table)
    story.append(Spacer(1, 20))

    net_data = [["LƯƠNG THỰC NHẬN:", f"{net_salary:,.0f} VNĐ"]]

    net_table = Table(net_data, colWidths=[3 * inch, 2.5 * inch])
    net_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0066CC")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F0F0")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ]
        )
    )
    story.append(net_table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()