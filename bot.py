"""
بوت تيليجرام للمساعدة في التوظيف
الأقسام: بناء السيرة الذاتية / المرشد المهني / التقديم للوظائف (بموافقة قبل الإرسال)

تشغيل: python bot.py
"""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db
from ai_client import career_advisor_reply, draft_application_email, polish_cv_summary
from config import (
    PORT,
    RENDER_EXTERNAL_URL,
    TELEGRAM_BOT_TOKEN,
    WEBHOOK_MODE,
    validate_config,
)
from email_sender import send_application_email
from pdf_generator import generate_cv_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- حالات محادثة بناء السيرة الذاتية ----------
(CV_NAME, CV_JOB_TITLE, CV_CONTACT, CV_SUMMARY, CV_EXPERIENCE,
 CV_EDUCATION, CV_SKILLS, CV_CONFIRM) = range(8)

# ---------- حالات محادثة التقديم على وظيفة ----------
(APP_EMAIL, APP_JOB_TITLE, APP_JOB_DETAILS, APP_CONFIRM) = range(100, 104)

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📄 بناء السيرة الذاتية"],
        ["🧭 المرشد المهني"],
        ["✉️ التقديم على وظيفة"],
        ["🏠 القائمة الرئيسية"],
    ],
    resize_keyboard=True,
)


def clear_mode(context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = None


# ==================== البداية والقائمة الرئيسية ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_user(user.id, user.full_name)
    clear_mode(context)
    await update.message.reply_text(
        f"أهلاً {user.first_name}! 👋\n\n"
        "أنا مساعدك الشخصي في التوظيف. أقدر أساعدك في:\n"
        "📄 بناء سيرة ذاتية احترافية\n"
        "🧭 تقديم استشارة مهنية\n"
        "✉️ صياغة وإرسال إيميلات تقديم على الوظائف (بعد موافقتك دائماً)\n\n"
        "اختر من القائمة تحت 👇",
        reply_markup=MAIN_MENU,
    )


async def main_menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يوجه الضغط على أزرار القائمة الرئيسية حسب النص، ويُستخدم أيضاً كمخرج لأي محادثة"""
    text = update.message.text
    if text == "📄 بناء السيرة الذاتية":
        return await cv_start(update, context)
    elif text == "🧭 المرشد المهني":
        return await advisor_start(update, context)
    elif text == "✉️ التقديم على وظيفة":
        return await app_start(update, context)
    elif text == "🏠 القائمة الرئيسية":
        clear_mode(context)
        await update.message.reply_text("رجعناك للقائمة الرئيسية 🏠", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    else:
        # إذا كان المستخدم في وضع المرشد المهني، حوّل الرسالة له
        if context.user_data.get("mode") == "advisor":
            await advisor_message(update, context)
        else:
            await update.message.reply_text("اختر من القائمة تحت 👇", reply_markup=MAIN_MENU)


# ==================== قسم 1: بناء السيرة الذاتية ====================

async def cv_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    context.user_data["cv_raw"] = {}
    await update.message.reply_text(
        "حلو! نبدأ ببناء سيرتك الذاتية 📄\n\n"
        "اكتب اسمك الكامل:",
        reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True),
    )
    return CV_NAME


async def cv_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["full_name"] = update.message.text
    await update.message.reply_text("ما هو المسمى الوظيفي اللي تستهدفه؟ (مثال: مطور برمجيات)")
    return CV_JOB_TITLE


async def cv_job_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["job_title"] = update.message.text
    await update.message.reply_text(
        "أرسل بيانات التواصل في رسالة وحدة بهذا الترتيب (كل واحدة بسطر):\n"
        "الإيميل\nرقم الجوال\nالمدينة"
    )
    return CV_CONTACT


async def cv_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [l.strip() for l in update.message.text.split("\n") if l.strip()]
    cv_raw = context.user_data["cv_raw"]
    cv_raw["email"] = lines[0] if len(lines) > 0 else ""
    cv_raw["phone"] = lines[1] if len(lines) > 1 else ""
    cv_raw["location"] = lines[2] if len(lines) > 2 else ""
    await update.message.reply_text(
        "اكتب نبذة مختصرة عن خبرتك ونقاط قوتك (جملتين إلى ثلاث، بأسلوبك العادي - "
        "بعدين بصيغها احترافياً):"
    )
    return CV_SUMMARY


async def cv_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["summary_raw"] = update.message.text
    await update.message.reply_text(
        "اذكر خبراتك العملية. لكل خبرة اكتب: المسمى الوظيفي - الشركة - الفترة - "
        "وصف مختصر للمهام. إذا عندك أكثر من خبرة افصل بينها بسطر جديد.\n\n"
        "إذا ما عندك خبرة بعد، اكتب: لا يوجد"
    )
    return CV_EXPERIENCE


async def cv_experience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["experience_raw"] = update.message.text
    await update.message.reply_text(
        "اذكر مؤهلاتك التعليمية: الدرجة - الجهة التعليمية - سنة التخرج (سطر لكل مؤهل)"
    )
    return CV_EDUCATION


async def cv_education(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["education_raw"] = update.message.text
    await update.message.reply_text("أخيراً، اذكر مهاراتك (افصل بينها بفاصلة):")
    return CV_SKILLS


async def cv_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cv_raw"]["skills_raw"] = update.message.text
    await update.message.reply_text("تمام، جاري صياغة سيرتك الذاتية احترافياً... ⏳")

    raw = context.user_data["cv_raw"]
    polished = polish_cv_summary(raw)

    cv_data = {
        "full_name": raw.get("full_name", ""),
        "job_title": raw.get("job_title", ""),
        "email": raw.get("email", ""),
        "phone": raw.get("phone", ""),
        "location": raw.get("location", ""),
        "summary": polished.get("summary", raw.get("summary_raw", "")),
        "experience": polished.get("experience", []),
        "education": polished.get("education", []),
        "skills": polished.get("skills", [s.strip() for s in raw.get("skills_raw", "").split(",") if s.strip()]),
    }

    user_id = update.effective_user.id
    db.save_cv_data(user_id, cv_data)
    pdf_path = generate_cv_pdf(user_id, cv_data)
    db.save_cv_pdf_path(user_id, pdf_path)

    with open(pdf_path, "rb") as f:
        await update.message.reply_document(f, filename="CV.pdf", caption="سيرتك الذاتية جاهزة ✅")

    await update.message.reply_text(
        "تقدر أي وقت تطلب مني تحدّثها من جديد، أو تستخدم زر (التقديم على وظيفة) "
        "عشان أرسلها لجهات التوظيف.",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


# ==================== قسم 2: المرشد المهني ====================

async def advisor_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "advisor"
    await update.message.reply_text(
        "أنا معك كمرشد مهني 🧭\n"
        "اسألني عن أي شي: تطوير مسارك، التحضير لمقابلة، تحديد مهارات ناقصة، "
        "أو أي قرار مهني تتردد فيه.\n\n"
        "اضغط 🏠 القائمة الرئيسية لما تبغى تطلع من هذا الوضع.",
        reply_markup=MAIN_MENU,
    )


async def advisor_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    cv_data = db.get_cv_data(user_id)
    history = db.get_advisor_history(user_id)

    reply = career_advisor_reply(user_id, cv_data, history, user_message)

    db.add_advisor_message(user_id, "user", user_message)
    db.add_advisor_message(user_id, "assistant", reply)

    await update.message.reply_text(reply)


# ==================== قسم 3: التقديم على وظيفة ====================

async def app_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    user_id = update.effective_user.id
    if not db.get_cv_data(user_id):
        await update.message.reply_text(
            "لاحظت ما عندك سيرة ذاتية محفوظة بعد. خلنا نبنيها أول عشان أقدر "
            "أستخدمها بإيميل التقديم.",
            reply_markup=MAIN_MENU,
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "تمام، عطني إيميل جهة التوظيف اللي تبي تقدم لها:",
        reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True),
    )
    return APP_EMAIL


async def app_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    if "@" not in email:
        await update.message.reply_text("هذا ما يبدو إيميل صحيح، تأكد وأرسله مرة ثانية:")
        return APP_EMAIL
    context.user_data["app_email"] = email
    await update.message.reply_text("وش المسمى الوظيفي للوظيفة اللي تقدم لها؟")
    return APP_JOB_TITLE


async def app_job_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["app_job_title"] = update.message.text
    await update.message.reply_text(
        "أعطني أي تفاصيل إضافية عن الوظيفة أو الشركة تحب أذكرها بالإيميل "
        "(أو اكتب: لا يوجد)"
    )
    return APP_JOB_DETAILS


async def app_job_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["app_job_details"] = update.message.text
    await update.message.reply_text("جاري صياغة إيميل التقديم... ⏳")

    user_id = update.effective_user.id
    cv_data = db.get_cv_data(user_id)
    draft = draft_application_email(
        cv_data,
        context.user_data["app_job_title"],
        context.user_data["app_job_details"],
        context.user_data["app_email"],
    )
    context.user_data["app_draft"] = draft

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ إرسال", callback_data="app_send")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="app_cancel")],
    ])
    await update.message.reply_text(
        f"📧 <b>إلى:</b> {context.user_data['app_email']}\n"
        f"📌 <b>الموضوع:</b> {draft.get('subject','')}\n\n"
        f"{draft.get('body','')}\n\n"
        "راجع الإيميل قبل، وإذا موافق اضغط إرسال 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
    return APP_CONFIRM


async def app_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "app_cancel":
        await query.edit_message_text("تم إلغاء الإرسال ❌")
        return ConversationHandler.END

    draft = context.user_data.get("app_draft", {})
    to_email = context.user_data.get("app_email")
    pdf_path = db.get_cv_pdf_path(user_id)

    try:
        send_application_email(to_email, draft.get("subject", ""), draft.get("body", ""), pdf_path)
        await query.edit_message_text(f"تم إرسال الإيميل بنجاح إلى {to_email} ✅")
    except Exception as e:
        logger.exception("فشل إرسال الإيميل")
        await query.edit_message_text(f"صار خطأ أثناء الإرسال ⚠️\n{e}")

    return ConversationHandler.END


# ==================== إلغاء عام ====================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_mode(context)
    await update.message.reply_text("تم الإلغاء.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


def main():
    validate_config()
    db.init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    cv_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📄 بناء السيرة الذاتية$"), cv_start)],
        states={
            CV_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_name)],
            CV_JOB_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_job_title)],
            CV_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_contact)],
            CV_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_summary)],
            CV_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_experience)],
            CV_EDUCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_education)],
            CV_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, cv_skills)],
        },
        fallbacks=[MessageHandler(filters.Regex("^(إلغاء|🏠 القائمة الرئيسية)$"), cancel)],
    )

    app_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✉️ التقديم على وظيفة$"), app_start)],
        states={
            APP_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, app_email)],
            APP_JOB_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, app_job_title)],
            APP_JOB_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, app_job_details)],
            APP_CONFIRM: [CallbackQueryHandler(app_confirm_callback, pattern="^app_(send|cancel)$")],
        },
        fallbacks=[MessageHandler(filters.Regex("^(إلغاء|🏠 القائمة الرئيسية)$"), cancel)],
    )

    app.add_handler(cv_conv)
    app.add_handler(app_conv)

    # زر المرشد المهني + توجيه القائمة الرئيسية + استقبال رسائل وضع المرشد
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_router))

    if WEBHOOK_MODE:
        # وضع Render (أو أي استضافة ويب): نستقبل التحديثات عبر Webhook
        # نستخدم التوكن كمسار سري بدل مسار عام معروف
        webhook_path = TELEGRAM_BOT_TOKEN
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/{webhook_path}"
        logger.info("البوت شغال بوضع Webhook على %s", webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=webhook_url,
        )
    else:
        # وضع التشغيل المحلي (على جهازك)
        logger.info("البوت شغال بوضع Polling (محلي)...")
        app.run_polling()


if __name__ == "__main__":
    main()
