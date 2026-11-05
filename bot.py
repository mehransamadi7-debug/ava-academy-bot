import html
import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# -------------------- لاگ و تنظیمات --------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": "انگلیسی 🇬🇧",
    "de": "آلمانی 🇩🇪",
    "fr": "فرانسه 🇫🇷",
    "it": "ایتالیایی 🇮🇹",
}

QUESTIONS = {
    "en": [
        {"q": "1. My name ___ Sara.", "options": ["am", "is", "are", "be"], "answer": 1},
        {"q": "2. They ___ in Tehran.", "options": ["live", "lives", "lived", "living"], "answer": 0},
        {"q": "3. ___ you like tea?", "options": ["Do", "Does", "Are", "Is"], "answer": 0},
        {"q": "4. Last weekend, we ___ our grandparents.", "options": ["visit", "visited", "visiting", "visits"], "answer": 1},
        {"q": "5. She has worked here ___ 2020.", "options": ["for", "since", "from", "during"], "answer": 1},
        {"q": "6. If it ___ tomorrow, we'll stay home.", "options": ["rains", "rained", "will rain", "would rain"], "answer": 0},
        {"q": "7. I wish I ___ more time to travel.", "options": ["have", "had", "will have", "would have"], "answer": 1},
        {"q": "8. By the time we arrived, the film ___.", "options": ["starts", "has started", "had started", "started"], "answer": 2},
        {"q": "9. If they had booked earlier, they ___ a better price.", "options": ["will get", "would get", "would have got", "got"], "answer": 2},
        {"q": "10. No sooner ___ the meeting begun than the lights went out.", "options": ["has", "had", "did", "was"], "answer": 1},
    ],
    "de": [
        {"q": "1. Ich ___ Studentin.", "options": ["bin", "bist", "ist", "sind"], "answer": 0},
        {"q": "2. Wir ___ in Berlin.", "options": ["wohnen", "wohnt", "wohne", "wohnst"], "answer": 0},
        {"q": "3. ___ du heute Abend Zeit?", "options": ["Hast", "Haben", "Hat", "Hatte"], "answer": 0},
        {"q": "4. Letzte Woche ___ er seine Großeltern besucht.", "options": ["hat", "ist", "haben", "war"], "answer": 0},
        {"q": "5. Ich warte ___ den Bus.", "options": ["auf", "für", "an", "mit"], "answer": 0},
        {"q": "6. Wenn ich reich ___, würde ich um die Welt reisen.", "options": ["wäre", "bin", "war", "sei"], "answer": 0},
        {"q": "7. Sie sagte, sie ___ später kommen.", "options": ["werde", "wird", "werden", "würde"], "answer": 0},
        {"q": "8. Nachdem er die E-Mail ___, rief er mich an.", "options": ["gelesen hatte", "hat gelesen", "liest", "gelesen hat"], "answer": 0},
        {"q": "9. Obwohl die Aufgabe schwierig ___, löste sie sie schnell.", "options": ["war", "ist", "wäre", "sei"], "answer": 0},
        {"q": "10. Hätte ich das früher gewusst, ___ ich dir Bescheid gesagt.", "options": ["hätte", "würde", "hatte", "werde"], "answer": 0},
    ],
    "fr": [
        {"q": "1. Je ___ Camille.", "options": ["m'appelle", "appelle", "me appelle", "s'appelle"], "answer": 0},
        {"q": "2. Nous ___ français.", "options": ["parlons", "parlez", "parlent", "parle"], "answer": 0},
        {"q": "3. Tu ___ un frère ?", "options": ["as", "a", "ai", "avons"], "answer": 0},
        {"q": "4. Hier, ils ___ au musée.", "options": ["sont allés", "ont allé", "sont allé", "allaient"], "answer": 0},
        {"q": "5. Elle habite ici ___ 2020.", "options": ["pendant", "depuis", "pour", "dans"], "answer": 1},
        {"q": "6. Si j'avais le choix, je ___ à l'étranger.", "options": ["voyagerais", "voyagerai", "voyage", "aurais voyagé"], "answer": 0},
        {"q": "7. Il faut que nous ___ à l'heure.", "options": ["soyons", "sommes", "serons", "étions"], "answer": 0},
        {"q": "8. Quand elle est arrivée, ses amis ___ déjà partis.", "options": ["étaient", "ont été", "étaient été", "avaient"], "answer": 0},
        {"q": "9. Bien qu'il ___ beaucoup, il a échoué.", "options": ["ait étudié", "a étudié", "avait étudié", "étudie"], "answer": 0},
        {"q": "10. Non seulement elle a terminé le projet, ___ elle a aussi formé l'équipe.", "options": ["mais", "et", "que", "donc"], "answer": 0},
    ],
    "it": [
        {"q": "1. Mi ___ Luca.", "options": ["chiamo", "chiama", "chiamano", "chiamate"], "answer": 0},
        {"q": "2. Noi ___ in Italia.", "options": ["viviamo", "vive", "vivono", "vivete"], "answer": 0},
        {"q": "3. Tu ___ un caffè?", "options": ["vuoi", "vuole", "voglio", "vogliamo"], "answer": 0},
        {"q": "4. Ieri loro ___ al mare.", "options": ["sono andati", "hanno andato", "è andato", "andavano"], "answer": 0},
        {"q": "5. Studio italiano ___ sei mesi.", "options": ["da", "per", "dal", "fa"], "answer": 0},
        {"q": "6. Se avessi una settimana libera, ___ in Sicilia.", "options": ["andrei", "andrò", "andavo", "vado"], "answer": 0},
        {"q": "7. Credo che loro ___ già partiti.", "options": ["siano", "sono", "erano", "essere"], "answer": 0},
        {"q": "8. Когда siamo arrivati, loro ___ già il negozio.", "options": ["avevano chiuso", "hanno chiuso", "chiudevano", "chiusero"], "answer": 0},
        {"q": "9. Benché ___ molto stanco, ha continuato a lavorare.", "options": ["fosse", "era", "è", "sarà"], "answer": 0},
        {"q": "10. Se me l'___ detto قبل prima, avrei potuto aiutarti.", "options": ["avessi", "avrei", "hai", "avevi"], "answer": 0},
    ],
}

GOALS = {
    "goal_migration": "مهاجرت و اقامت 🌍",
    "goal_travel": "مکالمه روان و سفر ✈️",
    "goal_exam": "آزمون‌های بین‌المللی (IELTS / TestDaF / DELF / CILS) 📜",
    "goal_career": "پیشرفت شغلی، مصاحبه و بیزینس 💼",
}

user_sessions = {}

def generate_attractive_report(user_first_name: str, language_name: str, score: int, goal: str) -> str:
    percentage = score * 10
    
    if score <= 2:
        level_code = "A1"
        level_title = "مبتدی (Starter / Breakthrough)"
        bar = "🟩⬜⬜⬜⬜"
        analysis = (
            "▫️ <b>وضعیت تسلط:</b> شما مفاهیم پایه‌ای و برخی واژگان اولیه را می‌شناسید، اما برای ساخت جملات پیوسته و مکالمه مستقل به آموزش ساختارمند نیاز دارید.\n"
            "▫️ <b>نقاط قوت:</b> علاقه و آمادگی کامل ذهن برای ساخت فونداسیون اصولی زبان.\n"
            "▫️ <b>مسیر پیشنهادی آوا:</b> ورود به دوره مکالمه مقدماتی فشرده با تمرکز بر شکستن سد مکالمه و تقویت تلفظ."
        )
    elif score <= 4:
        level_code = "A2"
        level_title = "پایه (Elementary / Waystage)"
        bar = "🟩🟩⬜⬜⬜"
        analysis = (
            "▫️ <b>وضعیت تسلط:</b> توانایی درک و ساخت جملات برای امور روزمره، خرید و معرفی. برای مکالمه بدون مکث و درک ساختارهای گذشته و آینده نیازمند تمرین بیشتر هستید.\n"
            "▫️ <b>نقاط قوت:</b> درک کلی ساختار زبان و توانایی رفع نیازهای اصلی روزمره.\n"
            "▫️ <b>مسیر پیشنهادی آوا:</b> دوره تقویت دایره لغات فعال و کارگاه‌های مکالمه موضوعی برای انتقال سریع به سطح متوسط."
        )
    elif score <= 6:
        level_code = "B1"
        level_title = "متوسط (Intermediate / Threshold)"
        bar = "🟩🟩🟩⬜⬜"
        analysis = (
            "▫️ <b>وضعیت تسلط:</b> شما از نقطه عطف یادگیری عبور کرده‌اید! توانایی توضیح تجربیات شخصی، اهداف و برنامه‌ها را دارید. چالش اصلی شما تسلط بر گرامرهای ترکیبی و گسترش اصطلاحات روزمره است.\n"
            "▫️ <b>نقاط قوت:</b> استقلال نسبی زبانی و اعتمادبه‌نفس در گفتگو.\n"
            "▫️ <b>مسیر پیشنهادی آوا:</b> شرکت در دوره‌های آمادگی آزمون یا کلاس‌های بحث آزاد (Free Discussion) آکادمی جهت رسیدن به تسلط کامل."
        )
    elif score <= 8:
        level_code = "B2"
        level_title = "متوسط رو به بالا (Vantage / Upper-Intermediate)"
        bar = "🟩🟩🟩🟩⬜"
        analysis = (
            "▫️ <b>وضعیت تسلط:</b> تسلط تحسین‌برانگیز! شما قادر به تحلیل موضوعات پیچیده، درک اخبار و مکالمه طبیعی با گویشوران بومی هستید. تنها جزئیات ساختاری و اصطلاحات پیشرفته نیازمند صیقل‌کاری هستند.\n"
            "▫️ <b>نقاط قوت:</b> تسلط بالا بر ساختارهای گرامری و سرعت پردازش ذهنی زبان.\n"
            "▫️ <b>مسیر پیشنهادی آوا:</b> دوره‌های تخصصی آمادگی آزمون برای نمرات تاپ یا دوره‌های Business Language برای کار و مهاجرت تخصصی."
        )
    else:
        level_code = "C1"
        level_title = "پیشرفته (Effective Operational Proficiency)"
        bar = "🟩🟩🟩🟩🟩"
        analysis = (
            "▫️ <b>وضعیت تسلط:</b> تبریک! شما به سطحی از تسلط رسیده‌اید که زبان را کاملاً منعطف، دقیق و بدون احساس خستگی در محیط‌های تحصیلی و کاری سطح اول بین‌المللی به کار می‌برید.\n"
            "▫️ <b>نقاط قوت:</b> دقت ساختاری فوق‌العاده و درک عمیق مفاهیم ضمنی و اصطلاحات زبان.\n"
            "▫️ <b>مسیر پیشنهادی آوا:</b> کارگاه‌های پیشرفته نگارش آکادمیک و تکنیک‌های نمره ۸ به بالای آیلتس/سطوح معادل."
        )

    report = (
        f"📋 <b>کارنامه جامع تعیین سطح هوشمند آکادمی آوا</b>\n"
        f"═══════════════════\n"
        f"👤 <b>زبان‌آموز:</b> {html.escape(user_first_name)}\n"
        f"🌐 <b>زبان سنجش‌شده:</b> {language_name}\n"
        f"🎯 <b>هدف اعلام‌شده:</b> {html.escape(goal)}\n\n"
        f"📊 <b>نتیجه ارزیابی:</b>\n"
        f"▫️ نمره آزمون: <b>{score} از ۱۰</b> (میزان تسلط: <b>{percentage}%</b>)\n"
        f"▫️ شاخص پیشرفت: {bar}\n"
        f"▫️ سطح طبق استاندارد CEFR اروپا: <b>{level_code} — {level_title}</b>\n\n"
        f"🔍 <b>تحلیل اختصاصی کارشناسان آموزشی:</b>\n"
        f"{analysis}\n\n"
        f"═══════════════════\n"
        f"🎁 <b>هدیه ویژه شما از طرف آکادمی آوا:</b>\n"
        f"یک جلسه مشاوره تخصصی آموزشی و تنظیم نقشه راه یادگیری با کارشناسان ارشد آوا برای شما رزرو شد. مشاوران ما به زودی با شما تماس خواهند گرفت. 📞✨"
    )
    return report

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    user_sessions[user.id] = {
        "state": "choosing_language",
        "score": 0,
        "question_index": 0,
    }

    keyboard = [
        [InlineKeyboardButton("🇬🇧 انگلیسی", callback_data="lang:en"), InlineKeyboardButton("🇩🇪 آلمانی", callback_data="lang:de")],
        [InlineKeyboardButton("🇫🇷 فرانسه", callback_data="lang:fr"), InlineKeyboardButton("🇮🇹 ایتالیایی", callback_data="lang:it")],
    ]

    welcome_text = (
        f"سلام {html.escape(user.first_name)} عزیز! به <b>آکادمی زبان‌های خارجی آوا</b> خوش آمدید 🎓✨\n\n"
        "این ربات با آزمون استاندارد ۱۰ سؤالی، سطح زبانی شما را طبق چارچوب مرجع اروپایی (CEFR) تحلیل کرده و کارنامه اختصاصی صادر می‌کند.\n\n"
        "📌 <i>لطفاً زبانی که مایل به ارزیابی آن هستید را انتخاب کنید:</i>"
    )
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    language = query.data.split(":", 1)[1]

    if language not in QUESTIONS:
        await query.edit_message_text("این زبان یافت نشد. لطفاً /start را بزنید.")
        return

    user_sessions[user_id] = {
        "state": "quiz",
        "language": language,
        "score": 0,
        "question_index": 0,
    }

    await query.edit_message_text(
        f"✅ زبان انتخابی شما: <b>{LANGUAGES[language]}</b>\n\n"
        "آزمون ۱۰ سؤالی آغاز شد. برای هر سؤال تنها یک گزینه را انتخاب نمایید. موفق باشید! 🎯",
        parse_mode="HTML",
    )
    await send_question(query.message.chat_id, user_id, context)

async def send_question(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = user_sessions.get(user_id)
    if not session:
        return

    language = session["language"]
    q_idx = session["question_index"]
    question = QUESTIONS[language][q_idx]

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"ans:{q_idx}:{opt_idx}")]
        for opt_idx, opt in enumerate(question["options"])
    ]

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"❓ <b>سؤال {q_idx + 1} از ۱۰</b>\n\n{html.escape(question['q'])}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    session["current_msg_id"] = msg.message_id

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    session = user_sessions.get(user_id)

    if not session or session.get("state") != "quiz":
        await query.answer("آزمون فعال نیست. لطفاً /start را بزنید.", show_alert=True)
        return

    try:
        _, q_idx_str, opt_idx_str = query.data.split(":")
        q_idx = int(q_idx_str)
        opt_idx = int(opt_idx_str)
    except Exception:
        await query.answer("پاسخ نامعتبر.", show_alert=True)
        return

    if q_idx != session["question_index"] or query.message.message_id != session.get("current_msg_id"):
        await query.answer("این سؤال قبلاً پاسخ داده شده است.", show_alert=True)
        return

    language = session["language"]
    if opt_idx == QUESTIONS[language][q_idx]["answer"]:
        session["score"] += 1

    session["question_index"] += 1
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    if session["question_index"] < len(QUESTIONS[language]):
        await send_question(query.message.chat_id, user_id, context)
    else:
        session["state"] = "awaiting_goal"
        keyboard = [
            [InlineKeyboardButton("مهاجرت و اقامت 🌍", callback_data="goal_migration")],
            [InlineKeyboardButton("مکالمه روان و سفر ✈️", callback_data="goal_travel")],
            [InlineKeyboardButton("آزمون‌های بین‌المللی (IELTS/...) 📜", callback_data="goal_exam")],
            [InlineKeyboardButton("پیشرفت شغلی، کاری و تحصیلی 💼", callback_data="goal_career")],
        ]
        finish_text = (
            "🎉 <b>پاسخ‌های شما با موفقیت ثبت شد!</b>\n\n"
            "🧠 سیستم هوشمند آوا در حال تحلیل پاسخ‌ها، درصد تسلط و سطح دقیق CEFR شماست.\n\n"
            "🎯 <i>برای اینکه نقشه راه و تحلیل دقیق متناسب با نیاز شما صادر شود، لطفاً <b>هدف اصلی</b> خود را انتخاب کنید:</i>"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=finish_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )

async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    session = user_sessions.get(user_id)

    if not session or session.get("state") != "awaiting_goal":
        await query.answer("لطفاً با /start از ابتدا شروع کنید.", show_alert=True)
        return

    goal_key = query.data
    goal_text = GOALS.get(goal_key, "نامشخص")
    session["goal"] = goal_text
    session["state"] = "awaiting_contact"

    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    contact_btn = ReplyKeyboardMarkup(
        [[KeyboardButton("📊 مشاهده کارنامه و دریافت مشاوره تخصصی 📱", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    lead_gate_text = (
        f"✨ هدف شما (<b>{goal_text}</b>) با موفقیت در پرونده ثبت شد!\n\n"
        "📑 <b>کارنامه تحلیلی شما آماده نمایش است:</b>\n"
        "▫️ سطح استاندارد بین‌المللی (CEFR)\n"
        "▫️ نمودار و درصد تسلط زبانی\n"
        "▫️ تحلیل نقاط قوت و ضعف\n"
        "▫️ پیشنهاد نقشه راه اختصاصی آکادمی آوا\n\n"
        "👇 <b>برای مشاهده فوری کارنامه کامل و رزرو مشاوره رایگان، لطفاً دکمه زیر را لمس نمایید:</b>"
    )
    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=lead_gate_text,
        reply_markup=contact_btn,
        parse_mode="HTML",
    )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message

    if not user or not message or not message.contact:
        return

    session = user_sessions.get(user.id)
    if not session or session.get("state") != "awaiting_contact":
        await message.reply_text("برای شروع مجدد، دستور /start را ارسال کنید.", reply_markup=ReplyKeyboardRemove())
        return

    phone = message.contact.phone_number
    language_key = session.get("language", "en")
    lang_name = LANGUAGES.get(language_key, "نامشخص")
    score = session.get("score", 0)
    goal = session.get("goal", "نامشخص")

    # ۱. ارسال کارنامه به کاربر
    report_text = generate_attractive_report(user.first_name, lang_name, score, goal)
    await message.reply_text(report_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

    # ۲. ارسال گزارش به ادمین با قابلیت دیباگ کامل در لاگ
    admin_id_env = os.getenv("ADMIN_CHAT_ID", "").strip()
    logger.info(f"Trying to send lead for user {user.id} to ADMIN_CHAT_ID: '{admin_id_env}'")

    if admin_id_env:
        try:
            admin_chat_id = int(admin_id_env)
            lead_for_admin = (
                "🔥 <b>لید جدید از آزمون تعیین سطح آوا!</b>\n"
                "═══════════════════\n"
                f"👤 <b>نام کاربر:</b> {html.escape(user.first_name)} {html.escape(user.last_name or '')}\n"
                f"🔗 <b>یوزرنیم:</b> @{html.escape(user.username) if user.username else 'ندارد'}\n"
                f"🆔 <b>آیدی تلگرام:</b> <code>{user.id}</code>\n"
                f"📞 <b>شماره تماس:</b> <code>{html.escape(phone)}</code>\n"
                f"🌐 <b>زبان آزمون:</b> {lang_name}\n"
                f"📊 <b>نمره کسب‌شده:</b> {score} از ۱۰\n"
                f"🎯 <b>هدف متقاضی:</b> {html.escape(goal)}\n"
                "═══════════════════\n"
                "⚡️ <i>جهت پیگیری و تماس مشاوره در پنل ثبت شد.</i>"
            )
            await context.bot.send_message(chat_id=admin_chat_id, text=lead_for_admin, parse_mode="HTML")
            logger.info(f"SUCCESS: Lead successfully sent to admin chat id {admin_chat_id}")
        except Exception as e:
            logger.error(f"ERROR: Failed to send lead to admin! Exception: {e}")
    else:
        logger.warning("WARNING: ADMIN_CHAT_ID is empty or not set in Railway environment variables!")

    session["state"] = "completed"

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = user_sessions.get(update.effective_user.id) if update.effective_user else None
    if not session:
        await update.message.reply_text("برای شروع تعیین سطح رایگان آکادمی آوا، لطفاً /start را بزنید.")
    elif session.get("state") == "awaiting_contact":
        await update.message.reply_text("برای صدور و مشاهده کارنامه، لطفاً از دکمه «📊 مشاهده کارنامه و دریافت مشاوره تخصصی 📱» استفاده کنید.")
    elif session.get("state") == "quiz":
        await update.message.reply_text("لطفاً برای ثبت پاسخ، گزینه‌های داخل پیام سؤال را لمس کنید.")

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("متغیر BOT_TOKEN یافت نشد!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_handler, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(answer_handler, pattern=r"^ans:"))
    app.add_handler(CallbackQueryHandler(goal_handler, pattern=r"^goal_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("ربات آکادمی آوا با موفقیت اجرا شد.")
    app.run_polling()

if __name__ == "__main__":
    main()
