"""
توليد ملف PDF بسيط واحترافي للسيرة الذاتية باستخدام fpdf2
(fpdf2 يدعم النصوص العربية عبر خط يدعم RTL - نستخدم إعادة تشكيل الحروف بمكتبة
arabic_reshaper + python-bidi لعرض العربي بشكل صحيح داخل PDF)
"""
import os

import arabic_reshaper
from bidi.algorithm import get_display
from fpdf import FPDF

from config import CV_OUTPUT_DIR

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
# ضع خط يدعم العربية (مثل Amiri أو NotoNaskhArabic) داخل مجلد fonts باسم arabic.ttf
FONT_PATH = os.path.join(FONT_DIR, "arabic.ttf")


def _rtl(text: str) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _is_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in text or "")


class CVPdf(FPDF):
    def header(self):
        pass

    def footer(self):
        pass


def generate_cv_pdf(user_id: int, cv_data: dict) -> str:
    os.makedirs(CV_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(CV_OUTPUT_DIR, f"cv_{user_id}.pdf")

    pdf = CVPdf()
    pdf.add_page()

    has_arabic_font = os.path.exists(FONT_PATH)
    if has_arabic_font:
        pdf.add_font("Arabic", "", FONT_PATH, uni=True)

    def write_line(text, size=11, bold=False, align="L"):
        if not text:
            return
        style = "B" if bold else ""
        if has_arabic_font:
            pdf.set_font("Arabic", style, size)
            display_text = _rtl(text) if _is_arabic(text) else text
            # عكس المحاذاة تلقائياً للنص العربي
            real_align = "R" if _is_arabic(text) else align
        else:
            pdf.set_font("Helvetica", style, size)
            display_text = text
            real_align = align
        pdf.multi_cell(0, 8, display_text, align=real_align)

    name = cv_data.get("full_name", "")
    title = cv_data.get("job_title", "")
    contact = " | ".join(filter(None, [
        cv_data.get("email", ""),
        cv_data.get("phone", ""),
        cv_data.get("location", ""),
    ]))

    write_line(name, size=20, bold=True, align="C")
    write_line(title, size=13, align="C")
    write_line(contact, size=10, align="C")
    pdf.ln(4)

    summary = cv_data.get("summary", "")
    if summary:
        write_line("الملخص المهني" if _is_arabic(summary) else "Professional Summary", size=14, bold=True)
        write_line(summary)
        pdf.ln(3)

    experience = cv_data.get("experience", [])
    if experience:
        write_line("الخبرات العملية" if any(_is_arabic(e.get("title", "")) for e in experience) else "Experience",
                    size=14, bold=True)
        for exp in experience:
            line1 = f"{exp.get('title','')} - {exp.get('company','')} ({exp.get('period','')})"
            write_line(line1, size=12, bold=True)
            write_line(exp.get("description", ""))
            pdf.ln(1)
        pdf.ln(2)

    education = cv_data.get("education", [])
    if education:
        write_line("التعليم" if any(_is_arabic(e.get("degree", "")) for e in education) else "Education",
                    size=14, bold=True)
        for edu in education:
            line1 = f"{edu.get('degree','')} - {edu.get('institution','')} ({edu.get('period','')})"
            write_line(line1)
        pdf.ln(2)

    skills = cv_data.get("skills", [])
    if skills:
        write_line("المهارات" if any(_is_arabic(s) for s in skills) else "Skills", size=14, bold=True)
        write_line(" • ".join(skills))

    pdf.output(output_path)
    return output_path
