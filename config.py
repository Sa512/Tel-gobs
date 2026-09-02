"""
إعدادات البوت - كل المفاتيح السرية تُقرأ من ملف .env
لا تكتب أي مفتاح مباشرة في الكود
"""
import os
from dotenv import load_dotenv

load_dotenv()

# توكن بوت التيليجرام (تحصل عليه من @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# مفتاح Anthropic API (لتشغيل Claude - المرشد المهني وصياغة السيرة والإيميلات)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# إعدادات إرسال الإيميل عبر SMTP (مثال: Gmail)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")          # إيميلك اللي راح يرسل منه
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")   # App Password وليس كلمة مرور الحساب العادية

# مسار قاعدة البيانات
# على Render: وجّهه لمجلد الـ Persistent Disk (مثال: /data/job_bot.db) عشان البيانات
# ما تروح كل مرة يعيد فيها Render تشغيل الخدمة
DB_PATH = os.getenv("DB_PATH", "job_bot.db")

# مجلد حفظ ملفات السير الذاتية المولّدة
# نفس الملاحظة: وجّهه لمجلد الـ Persistent Disk على Render
CV_OUTPUT_DIR = os.getenv("CV_OUTPUT_DIR", "generated_cvs")

# ---------- إعدادات وضع Webhook (يُستخدم تلقائياً على Render) ----------
# Render يضبط هذا المتغير تلقائياً لأي Web Service = رابط الخدمة العام
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# البورت اللي لازم نستمع عليه (Render يحدده تلقائياً عبر PORT)
PORT = int(os.getenv("PORT", "10000"))

# إذا كان الرابط العام موجود (يعني نشتغل على Render) أو تم تفعيله يدوياً،
# نستخدم Webhook بدل Polling
WEBHOOK_MODE = bool(RENDER_EXTERNAL_URL) or os.getenv("WEBHOOK_MODE", "false").lower() == "true"

REQUIRED_VARS = {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
}


def validate_config():
    missing = [name for name, value in REQUIRED_VARS.items() if not value]
    if missing:
        raise RuntimeError(
            "المتغيرات التالية ناقصة في ملف .env: " + ", ".join(missing)
        )
