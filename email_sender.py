"""
إرسال إيميل التقديم عبر SMTP - يُستدعى فقط بعد موافقة المستخدم الصريحة
"""
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD


def send_application_email(to_email: str, subject: str, body: str, attachment_path: str | None = None):
    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError(
            "إعدادات الإيميل (SMTP_USER / SMTP_PASSWORD) غير مضبوطة في ملف .env"
        )

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    if attachment_path:
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), _subtype="pdf")
            part.add_header(
                "Content-Disposition", "attachment", filename="CV.pdf"
            )
            msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
