import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# مراحل مکالمه (States)
SELECTING_LANGUAGE, ASKING_QUESTION, SELECTING_GOAL, GET_CONTACT = range(4)

# بانک ۱۰ سوالی برای ۴ زبان (انگلیسی، آلمانی، فرانسوی، ایتالیایی)
QUIZ_DATA = {
    "انگلیسی": [
        {"q": "1. She _____ to the gym every morning.", "options": ["goes", "go", "going"], "a": 0},
        {"q": "2. I haven't seen him _____ last Monday.", "options": ["for", "since", "from"], "a": 1},
        {"q": "3. If it rains tomorrow, we _____ the picnic.", "options": ["cancel", "would cancel", "will cancel"], "a": 2},
        {"q": "4. The report _____ by the manager yesterday.", "options": ["was reviewed", "reviewed", "is reviewing"], "a": 0},
        {"q": "5. Which word is a synonym for 'Abundant'?", "options": ["Scarce", "Plentiful", "Tiny"], "a": 1},
        {"q": "6. He insisted _____ paying for the dinner.", "options": ["in", "to", "on"], "a": 2},
        {"q": "7. By next year, they _____ the construction.", "options": ["will finish", "will have finished", "finish"], "a": 1},
        {"q": "8. Hardly _____ entered the room when the phone rang.", "options": ["had he", "he had", "did he"], "a": 0},
        {"q": "9. She succeeded despite _____ many difficulties.", "options": ["she faced", "facing", "faced"], "a": 1},
        {"q": "10. Which idiom means 'to disclose a secret'?", "options": ["Bite the bullet", "Spill the beans", "Break a leg"], "a": 1},
    ],
    "آلمانی": [
        {"q": "1. Wie _____ du?", "options": ["heißt", "heißen", "heiß"], "a": 0},
        {"q": "2. Das ist _____ Buch von Peter.", "options": ["der", "die", "das"], "a": 2},
        {"q": "3. Wir fahren morgen _____ Berlin.", "options": ["nach", "in", "zu"], "a": 0},
        {"q": "4. Er hat gestern den ganzen Tag _____.", "options": ["gearbeitet", "arbeitet", "arbeiten"], "a": 0},
        {"q": "5. Ich helfe _____ (dem Mann / dir). Welcher Kasus steht nach 'helfen'?", "options": ["Akkusativ", "Dativ", "Genitiv"], "a": 1},
        {"q": "6. Wenn ich reich wäre, _____ ich eine Weltreise machen.", "options": ["wurde", "werde", "würde"], "a": 2},
        {"q": "7. Das Haus, _____ dort steht, ist sehr alt.", "options": ["das", "der", "welcher"], "a": 0},
        {"q": "8. Er wartet schon seit zwei Stunden _____ den Bus.", "options": ["auf", "für", "an"], "a": 0},
        {"q": "9. Obwohl es regnete, _____ wir spazieren.", "options": ["gingen", "haben gegangen", "gehen"], "a": 0},
        {"q": "10. Was bedeutet 'Verantwortung'?", "options": ["تصمیم‌گیری", "مسئولیت", "تجربه"], "a": 1},
    ],
    "فرانسوی": [
        {"q": "1. Comment vous _____ -vous ?", "options": ["appelez", "appelle", "appeler"], "a": 0},
        {"q": "2. Je _____ un café s'il vous plaît.", "options": ["veux", "voudrais", "vouloir"], "a": 1},
        {"q": "3. Hier, elle _____ au cinéma.", "options": ["est allée", "a allé", "va"], "a": 0},
        {"q": "4. Nous habitons _____ Paris.", "options": ["en", "au", "à"], "a": 2},
        {"q": "5. C'est la maison de Pierre, c'est _____ maison.", "options": ["sa", "son", "ses"], "a": 0},
        {"q": "6. Il faut que tu _____ tes devoirs.", "options": ["fasses", "fais", "faire"], "a": 0},
        {"q": "7. Si j'avais le temps, je _____ plus souvent.", "options": ["voyagerais", "voyagerai", "voyage"], "a": 0},
        {"q": "8. Les fleurs que j'ai _____ sont très belles.", "options": ["acheté", "achetées", "acheter"], "a": 1},
        {"q": "9. Que signifie l'expression 'Avoir le cafard' ?", "options": ["خوشحال بودن", "افسرده یا ناراحت بودن", "عجله داشتن"], "a": 1},
        {"q": "10. 'Bien que' doit être suivi de quel mode ?", "options": ["Indicatif", "Subjonctif", "Conditionnel"], "a": 1},
    ],
    "ایتالیایی": [
        {"q": "1. Come ti _____?", "options": ["chiami", "chiamo", "chiama"], "a": 0},
        {"q": "2. Oggi c'è _____ bel sole.", "options": ["un", "uno", "una"], "a": 0},
        {"q": "3. Ieri sera ho _____ una pizza con gli amici.", "options": ["mangiato", "mangio", "mangiare"], "a": 0},
        {"q": "4. Loro _____ a Roma da tre anni.", "options": ["abitano", "abita", "abitiamo"], "a": 0},
        {"q": "5. Domani _____ al mare se fa bel tempo.", "options": ["andiamo", "andavamo", "siamo andati"], "a": 0},
        {"q": "6. Penso che questo film _____ molto interessante.", "options": ["è", "sia", "fosse"], "a": 1},
        {"q": "7. Se potessi, _____ una casa in Toscana.", "options": ["comprerei", "comprerò", "ho comprato"], "a": 0},
        {"q": "8. I libri _____ ho comprato sono molto utili.", "options": ["che", "cui", "quale"], "a": 0},
        {"q": "9. Cosa significa l'espressione 'In bocca al lupo'?", "options": ["خطر بزرگ", "موفق باشی / آرزوی شانس", "غذای خوشمزه"], "a": 1},
        {"q": "10. Abbiamo finito tutto _____ studiare.", "options": ["senza", "prima", "dopo"], "a": 0},
    ]
}

LANGUAGE_MAP = {
    "🇺🇸 انگلیسی": "انگلیسی",
    "🇩🇪 آلمانی": "آلمانی",
    "🇫🇷 فرانسوی": "فرانسوی",
    "🇮🇹 ایتالیایی": "ایتالیایی"
}

def calculate_level(score: int) -> str:
    """تحلیل و تخمین سطح استاندارد CEFR بر اساس پاسخ‌ها"""
    if score <= 3:
        return "A1 - A2 (مقدماتی / پایه)"
    elif score <= 6:
        return "B1 (متوسط)"
    elif score <= 8:
        return "B2 (فوق متوسط / کاربردی)"
    else:
        return "C1 - C2 (پیشرفته / مسلط)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    welcome_text = (
        f"سلام {user.first_name} عزیز! به **آکادمی زبان‌های خارجی آوا** خوش آمدید 🎓✨\n\n"
        "این آزمون تعیین سطح هوشمند شامل **۱۰ سوال چندگزینه‌ای استاندارد** است "
        "تا سطح فعلی شما در کوتاه‌ترین زمان ارزیابی شود.\n\n"
        "لطفاً زبانی که مایل به تعیین سطح آن هستید را انتخاب کنید:"
    )
    
    keyboard = [
        [KeyboardButton("🇺🇸 انگلیسی"), KeyboardButton("🇩🇪 آلمانی")],
        [KeyboardButton("🇫🇷 فرانسوی"), KeyboardButton("🇮🇹 ایتالیایی")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECTING_LANGUAGE

async def language_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text not in LANGUAGE_MAP:
        await update.message.reply_text("لطفاً یکی از زبان‌های موجود در دکمه‌ها را انتخاب کنید.")
        return SELECTING_LANGUAGE

    selected_lang = LANGUAGE_MAP[text]
    context.user_data["language"] = selected_lang
    context.user_data["score"] = 0
    context.user_data["current_q"] = 0

    await update.message.reply_text(
        f"گزینه انتخابی شما: **زبان {selected_lang}**\n\n"
        "آزمون ۱۰ سوالی شما آماده است. گزینه‌ها را با دقت انتخاب کنید. موفق باشید! 🎯",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["language"]
    q_index = context.user_data["current_q"]
    questions = QUIZ_DATA[lang]

    if q_index < len(questions):
        item = questions[q_index]
        keyboard = [[KeyboardButton(opt)] for opt in item["options"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        
        prompt = f"📌 **سوال {q_index + 1} از {len(questions)}** ({lang}):\n\n{item['q']}"
        await update.message.reply_text(prompt, reply_markup=reply_markup, parse_mode="Markdown")
        return ASKING_QUESTION
    else:
        return await finish_quiz(update, context)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data["language"]
    q_index = context.user_data["current_q"]
    item = QUIZ_DATA[lang][q_index]
    
    user_choice = update.message.text
    correct_choice = item["options"][item["a"]]
    
    if user_choice == correct_choice:
        context.user_data["score"] += 1

    context.user_data["current_q"] += 1
    return await ask_question(update, context)

async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    score = context.user_data["score"]
    total = len(QUIZ_DATA[context.user_data["language"]])
    level = calculate_level(score)
    context.user_data["level"] = level

    result_text = (
        f"🏁 **نتیجه تعیین سطح شما در آکادمی آوا:**\n\n"
        f"🌐 زبان: **{context.user_data['language']}**\n"
        f"📊 نمره کسب‌شده: **{score} از {total}**\n"
        f"🏆 سطح تخمینی شما: **{level}**\n\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "جهت تدوین برنامه آموزشی دقیق و اختصاصی، **هدف اصلی** خود را مشخص کنید:"
    )

    goals = [
        [KeyboardButton("مهاجرت تحصیلی یا کاری ✈️")],
        [KeyboardButton("مکالمه روان و ارتباطات روزمره 🗣️")],
        [KeyboardButton("آمادگی آزمون‌های بین‌المللی 📝")],
        [KeyboardButton("پیشرفت شغلی و مذاکرات تجاری 💼")]
    ]
    reply_markup = ReplyKeyboardMarkup(goals, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(result_text, reply_markup=reply_markup, parse_mode="Markdown")
    return SELECTING_GOAL

async def goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["goal"] = update.message.text

    contact_button = KeyboardButton(text="📲 ارسال شماره تماس جهت دریافت مشاوره رایگان", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[contact_button]], resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "برای ثبت پرونده، رزرو جلسه تحلیل نتیجه و مشاوره تحصیلی رایگان، روی دکمه زیر کلیک کنید تا شماره تماس شما ارسال شود:\n\n"
        "*(همچنین می‌توانید شماره خود را به‌صورت متنی تایپ و ارسال کنید)*",
        reply_markup=reply_markup
    )
    return GET_CONTACT

async def contact_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    contact = update.message.contact
    phone_number = contact.phone_number if contact else update.message.text

    lang = context.user_data.get("language")
    score = context.user_data.get("score")
    level = context.user_data.get("level")
    goal = context.user_data.get("goal")

    # ساخت متن جامع برای گزارش لید
    lead_report = (
        "🔔 **یک لید جدید در آکادمی زبان‌های خارجی آوا ثبت شد!**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **نام و نام‌خانوادگی:** {user.full_name}\n"
        f"🆔 **آیدی تلگرام:** @{user.username if user.username else 'ندارد'}\n"
        f"🔢 **شناسه کاربری:** `{user.id}`\n"
        f"🌐 **زبان انتخابی:** {lang}\n"
        f"📝 **نمره:** {score} از ۱۰\n"
        f"📊 **سطح تخمینی:** {level}\n"
        f"🎯 **هدف متقاضی:** {goal}\n"
        f"📞 **شماره تماس:** `{phone_number}`\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    logger.info(f"New Lead: {phone_number} - {lang}")

    # ارسال مستقیم اطلاعات به پیوی ادمین
    admin_id = os.environ.get("ADMIN_CHAT_ID")
    if admin_id:
        try:
            await context.bot.send_message(chat_id=admin_id, text=lead_report, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send lead to admin: {e}")

    await update.message.reply_text(
        "🎉 **اطلاعات شما با موفقیت ثبت شد!**\n\n"
        "کارشناسان دپارتمان آموزش آکادمی آوا به‌زودی با شما تماس خواهند گرفت تا برنامه پیشنهادی و مسیر آموزشی شما را ارائه دهند.\n\n"
        "از اعتماد و همراهی شما سپاسگزاریم! 🌟",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("آزمون لغو شد. برای شروع دوباره دستور /start را بفرستید.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("خطا: BOT_TOKEN در متغیرهای محیطی یافت نشد.")
        return

    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_chosen)],
            ASKING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer)],
            SELECTING_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, goal_chosen)],
            GET_CONTACT: [MessageHandler(filters.CONTACT | (filters.TEXT & ~filters.COMMAND), contact_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    print("ربات آوا آماده به کار و روشن است...")
    application.run_polling()

if __name__ == "__main__":
    main()
