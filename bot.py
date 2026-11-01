import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Questions database for 4 languages (10 questions each)
QUESTIONS = {
    "en": [
        {"q": "1. Choose the correct form: She ___ to work every day.", "options": ["go", "goes", "going", "gone"], "correct": 1},
        {"q": "2. Choose the correct past tense: Yesterday, I ___ a book.", "options": ["buy", "buys", "bought", "buying"], "correct": 2},
        {"q": "3. Which sentence is correct?", "options": ["He can plays tennis.", "He can play tennis.", "He can playing tennis.", "He plays can tennis."], "correct": 1},
        {"q": "4. Complete the sentence: There ___ many people in the room.", "options": ["is", "are", "am", "be"], "correct": 1},
        {"q": "5. What is the comparative form of 'good'?", "options": ["gooder", "better", "best", "more good"], "correct": 1},
        {"q": "6. Choose the correct preposition: She is good ___ mathematics.", "options": ["at", "in", "on", "with"], "correct": 0},
        {"q": "7. Choose the correct modal: You ___ wear a helmet when riding a bike.", "options": ["should", "might", "can", "may"], "correct": 0},
        {"q": "8. Identify the present perfect tense:", "options": ["I ate lunch.", "I am eating lunch.", "I have eaten lunch.", "I will eat lunch."], "correct": 2},
        {"q": "9. Choose the correct passive voice: The letter ___ by John.", "options": ["wrote", "is written", "is write", "writing"], "correct": 1},
        {"q": "10. Complete the conditional: If I had money, I ___ a car.", "options": ["will buy", "bought", "would buy", "have bought"], "correct": 2}
    ],
    "de": [
        {"q": "1. Wählen Sie die richtige Form: Ich ___ aus Deutschland.", "options": ["bin", "bist", "ist", "sind"], "correct": 0},
        {"q": "2. Ergänzen Sie: Er ___ gern Kaffee.", "options": ["trinke", "trinkst", "trinkt", "trinken"], "correct": 2},
        {"q": "3. Welcher Satz ist richtig?", "options": ["Du hast ein Auto.", "Du hast eine Auto.", "Du hast einen Auto.", "Du hast eines Auto."], "correct": 0},
        {"q": "4. Wie heißt das Präteritum von 'gehen'?", "options": ["gegangen", "ging", "geht", "gehe"], "correct": 1},
        {"q": "5. Wählen Sie den Artikel: ___ Buch ist interessant.", "options": ["Der", "Die", "Das", "Den"], "correct": 2},
        {"q": "6. Ergänzen Sie die Präposition: Wir warten ___ den Bus.", "options": ["auf", "für", "an", "mit"], "correct": 0},
        {"q": "7. Welches Modalverb passt? Man ___ hier nicht rauchen.", "options": ["kann", "darf nicht", "muss", "will"], "correct": 1},
        {"q": "8. Perfekt: Gestern habe ich ein Buch ___.", "options": ["lesen", "lest", "gelesen", "las"], "correct": 2},
        {"q": "9. Komparativ von 'gut':", "options": ["guter", "besser", "am besten", "gut"], "correct": 1},
        {"q": "10. Konjunktiv II: An deiner Stelle ___ ich zu Hause bleiben.", "options": ["wäre", "hätte", "würde", "werde"], "correct": 2}
    ],
    "fr": [
        {"q": "1. Choisissez la bonne forme : Je ___ étudiant.", "options": ["suis", "es", "est", "sommes"], "correct": 0},
        {"q": "2. Complétez : Elle ___ français.", "options": ["parle", "parles", "parlent", "parlons"], "correct": 0},
        {"q": "3. Quel article convient ? C'est ___ fille.", "options": ["un", "une", "des", "le"], "correct": 1},
        {"q": "4. Le pluriel de 'le journal' :", "options": ["les journals", "les journals", "les journaux", "le journaux"], "correct": 2},
        {"q": "5. Choisissez le passé composé : Hier, je ___ au cinéma.", "options": ["suis allé", "ai allé", "suis aller", "ai allé"], "correct": 0},
        {"q": "6. Complétez la phrase : Il y a ___ livres sur la table.", "options": ["de", "des", "le", "un"], "correct": 1},
        {"q": "7. Quel temps exprime une habitude dans le passé ?", "options": ["Le futur", "L'imparfait", "Le présent", "Le passé simple"], "correct": 1},
        {"q": "8. Choisissez le pronom correct : Tu téléphones à tes parents ? Oui, je ___ téléphone.", "options": ["les", "leur", "lui", "en"], "correct": 1},
        {"q": "9. Le comparatif de supériorité de 'bon' :", "options": ["plus bon", "meilleur", "plus mieux", "le meilleur"], "correct": 1},
        {"q": "10. Le subjonctif présent de 'venir' (tu) :", "options": ["viennes", "viens", "veniez", "viennent"], "correct": 0}
    ],
    "it": [
        {"q": "1. Scegli la forma corretta: Io ___ italiano.", "options": ["sono", "sei", "è", "siamo"], "correct": 0},
        {"q": "2. Completa: Tu ___ una pizza.", "options": ["mangi", "mangia", "mangiamo", "mangiate"], "correct": 0},
        {"q": "3. Quale articolo si usa per 'studente'?", "options": ["Il", "Lo", "La", "I"], "correct": 1},
        {"q": "4. Passato prossimo: Ieri io ___ a casa.", "options": ["ho rimasto", "sono rimasto", "ho rimansto", "sono rimasta"], "correct": 1},
        {"q": "5. Scegli la preposizione: Vado ___ Roma.", "options": ["in", "a", "da", "su"], "correct": 1},
        {"q": "6. Il plurale di 'il libro' è:", "options": ["i libri", "le libri", "gli libri", "i libro"], "correct": 0},
        {"q": "7. Completa: Se avessi tempo, ___ un viaggio.", "options": ["farei", "farei", "farò", "faccia"], "correct": 0},
        {"q": "8. Pronome diretto: Hai visto Maria? Sì, ___ vista.", "options": ["l'ho", "lo ho", "le ho", "li ho"], "correct": 0},
        {"q": "9. Comparativo di minoranza di 'buono':", "options": ["meno buono", "peggiore", "più buono", "meno meglio"], "correct": 0},
        {"q": "10. Congiuntivo presente (tu) essere:", "options": ["sia", "sii", "siate", "siano"], "correct": 1}
    ]
}

LANG_NAMES = {
    "en": "انگلیسی",
    "de": "آلمانی",
    "fr": "فرانسه",
    "it": "ایتالیایی"
}

# Store user sessions in memory
user_data_store = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"سلام {user.first_name} عزیز! به آکادمی زبان‌های خارجی آوا خوش آمدید 🎓✨\n\n"
        "این آزمون تعیین سطح هوشمند شامل ۱۰ سوال چندگزینه‌ای استاندارد است تا سطح فعلی شما در کوتاه‌ترین زمان ارزیابی شود.\n\n"
        "لطفاً زبانی که مایل به تعیین سطح آن هستید را انتخاب کنید:"
    )
    keyboard = [
        [InlineKeyboardButton("🇬🇧 انگلیسی", callback_data="lang_en"), InlineKeyboardButton("🇩🇪 آلمانی", callback_data="lang_de")],
        [InlineKeyboardButton("🇫🇷 فرانسه", callback_data="lang_fr"), InlineKeyboardButton("🇮🇹 ایتالیایی", callback_data="lang_it")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        user_data_store[user_id] = {
            "lang": lang,
            "current_question": 0,
            "score": 0,
            "answers": []
        }
        lang_name = LANG_NAMES.get(lang, "زبان مورد نظر")
        await query.edit_message_text(
            text=f"گزینه انتخابی شما: زبان {lang_name}\n\nآزمون ۱۰ سوالی شما آماده است. گزینه‌ها را با دقت انتخاب کنید. موفق باشید! 🎯"
        )
        await send_question(query.message.chat_id, user_id, context)

    elif data.startswith("ans_"):
        if user_id not in user_data_store:
            await query.edit_message_text(text="لطفاً با زدن دستور /start آزمون را دوباره شروع کنید.")
            return

        selected_option = int(data.split("_")[1])
        session = user_data_store[user_id]
        lang = session["lang"]
        current_q_idx = session["current_question"]

        correct_option = QUESTIONS[lang][current_q_idx]["correct"]
        if selected_option == correct_option:
            session["score"] += 1

        session["current_question"] += 1

        if session["current_question"] < len(QUESTIONS[lang]):
            await send_question(query.message.chat_id, user_id, context)
        else:
            await finish_quiz(query.message.chat_id, user_id, context)

async def send_question(chat_id, user_id, context):
    session = user_data_store[user_id]
    lang = session["lang"]
    q_idx = session["current_question"]
    q_data = QUESTIONS[lang][q_idx]

    keyboard = []
    for idx, option in enumerate(q_data["options"]):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"ans_{idx}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=q_data["q"],
        reply_markup=reply_markup
    )

async def finish_quiz(chat_id, user_id, context):
    session = user_data_store[user_id]
    score = session["score"]
    lang_name = LANG_NAMES[session["lang"]]

    # Estimate CEFR level
    if score <= 3:
        level = "Beginner (A1)"
    elif score <= 6:
        level = "Elementary / Pre-Intermediate (A2)"
    elif score <= 8:
        level = "Intermediate (B1)"
    else:
        level = "Upper-Intermediate / Advanced (B2-C1)"

    session["level"] = level

    result_text = (
        f"🎉 آزمون تعیین سطح زبان {lang_name} به پایان رسید!\n\n"
        f"📊 تعداد پاسخ‌های صحیح: {score} از 10\n"
        f"🏆 سطح تقریبی شما: *{level}*\n\n"
        "برای ادامه و انتخاب هدف یادگیری، لطفاً گزینه هدف خود را انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("مهاجرت 🌍", callback_data="goal_migration")],
        [InlineKeyboardButton("مکالمه و سفر ✈️", callback_data="goal_travel")],
        [InlineKeyboardButton("آزمون‌های بین‌المللی (IELTS/TestDaF/...) 📜", callback_data="goal_exam")],
        [InlineKeyboardButton("پیشرفت شغلی و تحصیلی 💼", callback_data="goal_career")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=result_text, reply_markup=reply_markup, parse_mode="Markdown")

async def goal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("goal_"):
        goal_map = {
            "goal_migration": "مهاجرت 🌍",
            "goal_travel": "مکالمه و سفر ✈️",
            "goal_exam": "آزمون‌های بین‌المللی 📜",
            "goal_career": "پیشرفت شغلی و تحصیلی 💼"
        }
        goal_text = goal_map.get(data, "نامشخص")
        if user_id in user_data_store:
            user_data_store[user_id]["goal"] = goal_text

        contact_keyboard = [[KeyboardButton("ارسال شماره تماس 📱", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(contact_keyboard, one_time_keyboard=True, resize_keyboard=True)

        await query.edit_message_text(
            text=f"هدف شما ثبت شد: {goal_text}\n\nلطفاً برای دریافت مشاوره اختصاصی و هماهنگی کلاس‌ها، شماره تماس خود را از طریق دکمه زیر ارسال کنید:"
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="لطفاً روی دکمه زیر کلیک کنید تا شماره شما به موسسه ارسال شود:",
            reply_markup=reply_markup
        )

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    contact = update.message.contact
    user_id = user.id

    session = user_data_store.get(user_id, {})
    lang_name = LANG_NAMES.get(session.get("lang", "en"), "انگلیسی")
    level = session.get("level", "نامشخص")
    score = session.get("score", 0)
    goal = session.get("goal", "نامشخص")

    phone_number = contact.phone_number if contact else "دریافت نشده"

    lead_message = (
        f"🚨 *لید جدید ثبت شد!* (آکادمی آوا)\n\n"
        f"👤 نام: {user.first_name} {user.last_name or ''}\n"
        f"🔗 یوزرنیم: @{user.username or 'ندارد'}\n"
        f"🆔 آیدی تلگرام: `{user_id}`\n"
        f"🗣 زبان: {lang_name}\n"
        f"📊 نمره آزمون: {score}/10\n"
        f"🏆 سطح CEFR: {level}\n"
        f"🎯 هدف: {goal}\n"
        f"📞 شماره تماس: `{phone_number}`"
    )

    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=lead_message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Failed to send lead to admin: {e}")

    thanks_text = (
        "✅ اطلاعات شما با موفقیت ثبت شد!\n\n"
        "کارشناسان آکادمی زبان‌های خارجی آوا به زودی جهت مشاوره رایگان و برنامه‌ریزی کلاس‌ها با شما تماس خواهند گرفت. 🙏"
    )
    await update.message.reply_text(thanks_text, reply_markup=ReplyKeyboardRemove())

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN found in environment variables!")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(lang_|ans_)"))
    application.add_handler(CallbackQueryHandler(goal_handler, pattern="^goal_"))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
