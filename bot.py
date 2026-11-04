"""Ava language placement bot. Run with BOT_TOKEN set; optional ADMIN_CHAT_ID/BOT_DB_PATH."""
import html
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any

from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ContextTypes, MessageHandler, filters)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
LANGUAGES = {"en": "انگلیسی 🇬🇧", "de": "آلمانی 🇩🇪", "fr": "فرانسه 🇫🇷", "it": "ایتالیایی 🇮🇹"}
# A short, deterministic ten-item grammar check. It is an informal placement quiz, not a certified CEFR exam.
QUESTIONS = {
"en": [
("My name ___ Sara.", ["am","is","are","be"],1),("They ___ in Tehran.",["live","lives","lived","living"],0),
("___ you like tea?",["Do","Does","Are","Is"],0),("Last weekend, we ___ our grandparents.",["visit","visited","visiting","visits"],1),
("She has worked here ___ 2020.",["for","since","from","during"],1),("If it ___ tomorrow, we'll stay home.",["rains","rained","will rain","would rain"],0),
("I wish I ___ more time to travel.",["have","had","will have","would have"],1),("By the time we arrived, the film ___.",["starts","has started","had started","started"],2),
("If they had booked earlier, they ___ a better price.",["will get","would get","would have got","got"],2),("No sooner ___ the meeting begun than the lights went out.",["has","had","did","was"],1)],
"de": [
("Ich ___ Studentin.",["bin","bist","ist","sind"],0),("Wir ___ in Berlin.",["wohnen","wohnt","wohne","wohnst"],0),
("___ du heute Abend Zeit?",["Hast","Haben","Hat","Hatte"],0),("Letzte Woche ___ er seine Großeltern besucht.",["hat","ist","haben","war"],0),
("Ich warte ___ den Bus.",["auf","für","an","mit"],0),("Wenn ich reich ___, würde ich um die Welt reisen.",["wäre","bin","war","sei"],0),
("Sie sagte, sie ___ später kommen.",["werde","wird","werden","würde"],0),("Nachdem er die E-Mail ___, rief er mich an.",["gelesen hatte","hat gelesen","liest","gelesen hat"],0),
("Obwohl die Aufgabe schwierig ___, löste sie sie schnell.",["war","ist","wäre","sei"],0),("Hätte ich das früher gewusst, ___ ich dir Bescheid gesagt.",["hätte","würde","hatte","werde"],0)],
"fr": [
("Je ___ Camille.",["m'appelle","appelle","me appelle","s'appelle"],0),("Nous ___ français.",["parlons","parlez","parlent","parle"],0),
("Tu ___ un frère ?",["as","a","ai","avons"],0),("Hier, ils ___ au musée.",["sont allés","ont allé","sont allé","allaient"],0),
("Elle habite ici ___ 2020.",["pendant","depuis","pour","dans"],1),("Si j'avais le choix, je ___ à l'étranger.",["voyagerais","voyagerai","voyage","aurais voyagé"],0),
("Il faut que nous ___ à l'heure.",["soyons","sommes","serons","étions"],0),("Quand elle est arrivée, ses amis ___ déjà partis.",["étaient","ont été","étaient été","avaient"],0),
("Bien qu'il ___ beaucoup, il a échoué.",["ait étudié","a étudié","avait étudié","étudie"],0),("Non seulement elle a terminé le projet, ___ elle a aussi formé l'équipe.",["mais","et","que","donc"],0)],
"it": [
("Mi ___ Luca.",["chiamo","chiama","chiamano","chiamate"],0),("Noi ___ in Italia.",["viviamo","vive","vivono","vivete"],0),
("Tu ___ un caffè?",["vuoi","vuole","voglio","vogliamo"],0),("Ieri loro ___ al mare.",["sono andati","hanno andato","è andato","andavano"],0),
("Studio italiano ___ sei mesi.",["da","per","dal","fa"],0),("Se avessi una settimana libera, ___ in Sicilia.",["andrei","andrò","andavo","vado"],0),
("Credo che loro ___ già partiti.",["siano","sono","erano","essere"],0),("Quando siamo arrivati, loro ___ già il negozio.",["avevano chiuso","hanno chiuso","chiudevano","chiusero"],0),
("Benché ___ molto stanco, ha continuato a lavorare.",["fosse","era","è","sarà"],0),("Se me l'___ detto prima, avrei potuto aiutarti.",["avessi","avrei","hai","avevi"],0)]}
GOALS = {"goal_migration":"مهاجرت و اقامت 🌍", "goal_travel":"مکالمه و سفر ✈️", "goal_exam":"آزمون بین‌المللی 📜", "goal_career":"پیشرفت شغلی 💼", "goal_curious":"یادگیری و کنجکاوی 📚"}
CONSULTANT_WHATSAPP_URL = os.getenv("CONSULTANT_WHATSAPP_URL", "https://wa.me/989961665190").strip()
CONSULTATION_URL = os.getenv("CONSULTATION_URL", "https://avalanguage.net/#free-consultation").strip()
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://avalanguage.net").strip()

class Store:
    """Small SQLite persistence layer. Replacing a user's snapshot is an atomic transaction."""
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, session_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            # Aggregate-only funnel events; no user id, phone, or message text is stored here.
            db.execute("CREATE TABLE IF NOT EXISTS funnel_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    def put(self, user_id: int, session: dict[str, Any]) -> None:
        payload = json.dumps(session, ensure_ascii=False)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM users WHERE user_id=?", (int(user_id),))
            db.execute("INSERT INTO users(user_id, session_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (int(user_id), payload))
    def get(self, user_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT session_json FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return json.loads(row[0]) if row else None
    def track(self, event: str) -> None:
        allowed = {"bot_start", "intent_selected", "quiz_started", "quiz_completed", "result_shown",
                   "contact_prompt_shown", "contact_declined", "help_in_telegram",
                   "contact_consent_given", "phone_submitted", "consultation_menu_shown",
                   "advisor_option_shown_start", "advisor_option_shown_result"}
        if event not in allowed:
            raise ValueError("Unsupported funnel event")
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO funnel_events(event) VALUES (?)", (event,))

    def summary(self) -> dict[str, int]:
        with sqlite3.connect(self.path) as db:
            total, completed, leads = db.execute("SELECT COUNT(*), SUM(CASE WHEN json_extract(session_json,'$.state')='completed' OR json_extract(session_json,'$.result_shown')=1 THEN 1 ELSE 0 END), SUM(CASE WHEN json_extract(session_json,'$.consented_contact')=1 THEN 1 ELSE 0 END) FROM users").fetchone()
            events = dict(db.execute("SELECT event, COUNT(*) FROM funnel_events GROUP BY event").fetchall())
        result = {"users": total or 0, "completed": completed or 0, "consented_contacts": leads or 0}
        result.update({name: events.get(name, 0) for name in ("bot_start", "intent_selected", "quiz_started", "quiz_completed", "result_shown", "contact_prompt_shown", "contact_declined", "help_in_telegram", "contact_consent_given", "phone_submitted", "consultation_menu_shown", "advisor_option_shown_start", "advisor_option_shown_result")})
        return result

STORE = Store(os.getenv("BOT_DB_PATH", "ava_bot.sqlite3"))
user_sessions: dict[int, dict[str, Any]] = {}
def save(user_id: int) -> None:
    if user_id in user_sessions: STORE.put(user_id, user_sessions[user_id])
def load(user_id: int) -> dict[str, Any] | None:
    if user_id not in user_sessions:
        saved = STORE.get(user_id)
        if saved is not None: user_sessions[user_id] = saved
    return user_sessions.get(user_id)

def generate_attractive_report(user_first_name: str, language_name: str, score: int, goal: str) -> str:
    """Return a transparent quiz summary; the short quiz cannot certify CEFR proficiency."""
    score = max(0, min(10, int(score)))
    bands = [(2,"A1"),(4,"A2"),(6,"B1"),(8,"B2"),(10,"C1")]
    indicative = next(level for maximum, level in bands if score <= maximum)
    return ("📋 <b>گزارش آزمون کوتاه آوا</b>\n"
            f"👤 زبان‌آموز: {html.escape(user_first_name)}\n🌐 زبان: {html.escape(language_name)}\n"
            f"🎯 هدف: {html.escape(goal)}\n📊 پاسخ درست: <b>{score} از ۱۰ ({score*10}٪)</b>\n"
            f"سطح پیشنهادیِ تقریبی: <b>{indicative}</b> (برآورد مقدماتی، نه گواهی CEFR).\n\n"
            "این آزمون کوتاه فقط چند نکتهٔ دستوری را می‌سنجد و به‌تنهایی سطح زبان را به‌طور معتبر تعیین نمی‌کند. برای ارزیابی دقیق‌تر، مهارت گفتاری، شنیداری، خواندن و نوشتن نیز باید سنجیده شوند.\n"
            "برای ادامهٔ یادگیری، می‌توانید هدف خود را مرور کنید و با تمرین منظم پیش بروید.")

def consultation_menu_keyboard() -> InlineKeyboardMarkup:
    """External consultation options; opening a link is not recorded as a lead."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("گفت‌وگو با مشاور در واتساپ", url=CONSULTANT_WHATSAPP_URL)],
        [InlineKeyboardButton("درخواست مشاوره در وب‌سایت", url=CONSULTATION_URL)],
        [InlineKeyboardButton("دوره‌ها و وب‌سایت آوا", url=WEBSITE_URL)],
    ])

ADVISOR_BUTTON_LABEL = "گفت‌وگو با مشاور در واتساپ"

def advisor_button() -> InlineKeyboardButton:
    """Direct, user-initiated WhatsApp link. Opening it is not observable by the bot."""
    return InlineKeyboardButton(ADVISOR_BUTTON_LABEL, url=CONSULTANT_WHATSAPP_URL)

def result_keyboard() -> InlineKeyboardMarkup:
    """Primary direct advisor CTA first, then secondary website options."""
    return InlineKeyboardMarkup([
        [advisor_button()],
        [InlineKeyboardButton("درخواست مشاوره در وب‌سایت", url=CONSULTATION_URL)],
        [InlineKeyboardButton("دوره‌ها و وب‌سایت آوا", url=WEBSITE_URL)],
    ])

async def show_consultation_menu(message, *, track: bool = True, bot=None) -> None:
    """Send actionable options through a message or its chat when reply_text is unavailable."""
    text = ("برای دریافت مشاوره یکی از راه‌های زیر را انتخاب کنید. "
            "برای مشاوره در واتساپ، گفت‌وگو با مشاور را باز کنید و پیام خود را شخصاً ارسال کنید؛ "
            "ربات هیچ پیامی را خودکار منتقل نمی‌کند. زمان پاسخ‌گویی تضمین‌شده‌ای وجود ندارد. "
            "بازشدن لینک یا ارسال فرم در این ربات قابل مشاهده یا شمارش نیست.")
    markup = consultation_menu_keyboard()
    reply_text = getattr(message, "reply_text", None)
    if callable(reply_text):
        await reply_text(text, reply_markup=markup)
    else:
        chat_id = getattr(message, "chat_id", None)
        if chat_id is None:
            chat_id = getattr(getattr(message, "chat", None), "id", None)
        if bot is None or chat_id is None:
            raise ValueError("Cannot send consultation menu: no reply method or chat sender")
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    if track:
        STORE.track("consultation_menu_shown")

async def consultation_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await show_consultation_menu(update.message)

def _user(update: Update):
    return update.effective_user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _user(update)
    if not user or not update.message: return
    user_sessions[user.id] = {"state":"choosing_intent", "score":0, "question_index":0}
    save(user.id); STORE.track("bot_start"); STORE.track("advisor_option_shown_start")
    kb = [[advisor_button()],
          [InlineKeyboardButton("می‌خواهم یادگیری را شروع/جدی‌تر کنم",callback_data="intent:learn")],
          [InlineKeyboardButton("فقط می‌خواهم سطح مکالمه‌ام را بدانم",callback_data="intent:know")],
          [InlineKeyboardButton("فقط کنجکاوم",callback_data="intent:curious")],
          [InlineKeyboardButton("رد کردن و رفتن به آزمون",callback_data="intent:skip")]]
    await update.message.reply_text(f"سلام {html.escape(user.first_name or 'دوست عزیز')}! به <b>آکادمی زبان آوا</b> خوش آمدید.\nاین آزمون کوتاه آموزشی است و برآورد آن گواهی رسمی CEFR نیست.\n\nبرای شخصی‌سازی تجربه، نیت شما چیست؟ این انتخاب اختیاری است و در هر صورت می‌توانید آزمون رایگان را انجام دهید.\nاگر همین حالا می‌خواهید مستقیم با مشاور در واتساپ گفت‌وگو کنید، بدون آزمون و بدون ارائهٔ شماره به ربات، دکمهٔ «گفت‌وگو با مشاور در واتساپ» را بزنید؛ گفت‌وگو را خودتان آغاز می‌کنید و ربات بازشدن لینک را نمی‌بیند و شمارش نمی‌کند.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def send_question(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = load(user_id)
    if not session or session.get("state") != "quiz": return
    idx = session["question_index"]; question = QUESTIONS[session["language"]][idx]
    kb = [[InlineKeyboardButton(opt, callback_data=f"ans:{idx}:{n}")] for n,opt in enumerate(question[1])]
    msg = await context.bot.send_message(chat_id=chat_id, text=f"❓ <b>سؤال {idx+1} از ۱۰</b>\n\n{html.escape(question[0])}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    session["current_msg_id"] = msg.message_id; save(user_id)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    data = query.data or ""; user_id = query.from_user.id
    if data.startswith("intent:"):
        intent = data.partition(":")[2]
        labels = {"learn":"یادگیری را شروع/جدی‌تر می‌کنم", "know":"فقط می‌خواهم سطح مکالمه‌ام را بدانم", "curious":"فقط کنجکاوم"}
        if intent == "skip":
            session = load(user_id)
            if not session or session.get("state") != "choosing_intent":
                await query.answer("این مرحله فعال نیست.", show_alert=True); return
            session.pop("intent", None); session["state"] = "choosing_language"
            user_sessions[user_id] = session; save(user_id); await query.answer()
            kb = [[InlineKeyboardButton("🇬🇧 انگلیسی",callback_data="lang:en"),InlineKeyboardButton("🇩🇪 آلمانی",callback_data="lang:de")],
                  [InlineKeyboardButton("🇫🇷 فرانسه",callback_data="lang:fr"),InlineKeyboardButton("🇮🇹 ایتالیایی",callback_data="lang:it")]]
            await query.edit_message_text("بدون ثبت نیت هم می‌توانید آزمون را انجام دهید. زبان موردنظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb)); return
        if intent not in labels:
            await query.answer("گزینه نامعتبر است.", show_alert=True); return
        session = load(user_id) or {"score":0,"question_index":0}
        if session.get("state") != "choosing_intent":
            await query.answer("این مرحله فعال نیست.", show_alert=True); return
        session["intent"] = intent; session["state"] = "choosing_language"; user_sessions[user_id] = session
        save(user_id); STORE.track("intent_selected"); await query.answer()
        kb = [[InlineKeyboardButton("🇬🇧 انگلیسی",callback_data="lang:en"),InlineKeyboardButton("🇩🇪 آلمانی",callback_data="lang:de")],
              [InlineKeyboardButton("🇫🇷 فرانسه",callback_data="lang:fr"),InlineKeyboardButton("🇮🇹 ایتالیایی",callback_data="lang:it")]]
        await query.edit_message_text("ممنون! انتخاب شما مانع آزمون یا دریافت نتیجه نیست.\n\nزبان موردنظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb)); return
    if data.startswith("lang:"):
        language = data.partition(":")[2]
        if language not in QUESTIONS:
            await query.answer("زبان نامعتبر است.", show_alert=True); return
        previous = load(user_id) or {}
        user_sessions[user_id] = {"state":"quiz","language":language,"score":0,"question_index":0}
        if previous.get("intent") is not None:
            user_sessions[user_id]["intent"] = previous["intent"]
        save(user_id); STORE.track("quiz_started"); await query.answer()
        await query.edit_message_text(f"✅ زبان انتخابی: <b>{LANGUAGES[language]}</b>\nآزمون ۱۰ سؤالی آغاز شد.", parse_mode="HTML")
        await send_question(query.message.chat_id, user_id, context); return
    session = load(user_id)
    if data.startswith("ans:"):
        if not session or session.get("state") != "quiz":
            await query.answer("آزمون فعالی نیست؛ /start را بزنید.", show_alert=True); return
        try:
            _, raw_idx, raw_opt = data.split(":"); idx, opt = int(raw_idx), int(raw_opt)
        except (ValueError, TypeError):
            await query.answer("پاسخ نامعتبر است.", show_alert=True); return
        lang = session.get("language"); qi = session.get("question_index", -1)
        if lang not in QUESTIONS or idx != qi or idx >= len(QUESTIONS[lang]) or opt not in range(4) or query.message.message_id != session.get("current_msg_id"):
            await query.answer("این سؤال قبلاً پاسخ داده شده یا نامعتبر است.", show_alert=True); return
        if opt == QUESTIONS[lang][idx][2]: session["score"] += 1
        session["question_index"] += 1; save(user_id); await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        if session["question_index"] < len(QUESTIONS[lang]): await send_question(query.message.chat_id,user_id,context)
        else:
            session["state"]="awaiting_goal"; save(user_id); STORE.track("quiz_completed")
            kb=[[InlineKeyboardButton(label,callback_data=key)] for key,label in GOALS.items()]
            await context.bot.send_message(chat_id=query.message.chat_id,text="آزمون تمام شد. هدف یادگیری خود را انتخاب کنید:",reply_markup=InlineKeyboardMarkup(kb));
        return
    if data in GOALS:
        if not session or session.get("state") != "awaiting_goal":
            await query.answer("لطفاً با /start آغاز کنید.",show_alert=True); return
        session["goal"]=GOALS[data]; session["state"]="awaiting_contact"; session["result_shown"]=True; save(user_id)
        await query.answer(); await query.edit_message_reply_markup(reply_markup=None)
        lang=LANGUAGES.get(session.get("language"),"نامشخص")
        await context.bot.send_message(chat_id=query.message.chat_id,
            text=generate_attractive_report(query.from_user.first_name or "زبان‌آموز",lang,session.get("score",0),session.get("goal","نامشخص"))
                 + "\n\nبرای گفت‌وگوی مستقیم با مشاور در واتساپ، دکمهٔ زیر را بزنید؛ آزمون، انتخاب نیت یا ارسال شماره به ربات لازم نیست. گفت‌وگو را خودتان آغاز می‌کنید و ربات بازشدن لینک یا ارسال پیام در واتساپ را نمی‌بیند و شمارش نمی‌کند. گزینه‌های فرم مشاوره و وب‌سایت آوا هم در ادامهٔ همان دکمه‌ها موجود است.",
            parse_mode="HTML", reply_markup=result_keyboard())
        STORE.track("result_shown"); STORE.track("advisor_option_shown_result")
        kb=ReplyKeyboardMarkup([[KeyboardButton("📱 (اختیاری) با رضایت، شماره‌ام را برای پیگیری می‌فرستم",request_contact=True)]],resize_keyboard=True,one_time_keyboard=True)
        ikb=InlineKeyboardMarkup([[InlineKeyboardButton("راهنمایی و گزینه‌های مشاوره",callback_data="contact_help")],
                                  [InlineKeyboardButton("فعلاً تماس نمی‌خواهم",callback_data="contact_skip")]])
        await context.bot.send_message(chat_id=query.message.chat_id,text="ارسال شماره کاملاً اختیاری است و برای دیدن نتیجه یا گفت‌وگو با مشاور در واتساپ لازم نیست؛ گفت‌وگوی واتساپ را خودتان آغاز می‌کنید. فقط اگر خودتان دکمهٔ اشتراک‌گذاری مخاطب را بزنید، شمارهٔ خودتان برای پیگیری به ربات ارسال می‌شود. برای ادامهٔ گفت‌وگو با مشاور، از دکمهٔ واتساپ در همان پیام نتیجه استفاده کنید یا گزینه‌های زیر را بزنید.",reply_markup=kb)
        await context.bot.send_message(chat_id=query.message.chat_id,text="انتخاب با شماست:",reply_markup=ikb)
        STORE.track("contact_prompt_shown"); return
    if data in ("contact_skip", "contact_help"):
        if not session or session.get("state") != "awaiting_contact":
            await query.answer("این مرحله فعال نیست.",show_alert=True); return
        is_help = data == "contact_help"
        session["state"]="completed"; session["consented_contact"]=False; save(user_id)
        STORE.track("help_in_telegram" if is_help else "contact_declined")
        await query.answer(); await query.edit_message_reply_markup(reply_markup=None)
        if is_help:
            await context.bot.send_message(chat_id=query.message.chat_id,
                text="نتیجهٔ شما همچنان در دسترس است و ارائهٔ شماره لازم نیست.",
                reply_markup=ReplyKeyboardRemove())
            await show_consultation_menu(query.message, track=True, bot=context.bot)
        else:
            await context.bot.send_message(chat_id=query.message.chat_id,
                text="کاملاً قابل‌درک است؛ نتیجهٔ شما محفوظ است و نیازی به ارائهٔ شماره نیست. هر زمان خواستید می‌توانید دوباره /start را بزنید.",
                reply_markup=ReplyKeyboardRemove())
        return
    await query.answer("درخواست نامعتبر است.", show_alert=True)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user= _user(update); message=update.message
    if not user or not message or not message.contact: return
    session=load(user.id)
    if not session or session.get("state") != "awaiting_contact":
        await message.reply_text("برای شروع، /start را ارسال کنید.",reply_markup=ReplyKeyboardRemove()); return
    contact=message.contact
    if contact.user_id != user.id:
        await message.reply_text("لطفاً فقط مخاطب خودتان را با دکمهٔ اشتراک‌گذاری تلگرام ارسال کنید.",reply_markup=ReplyKeyboardRemove()); return
    phone=contact.phone_number
    # Telegram's explicit share-contact action is the user's affirmative consent.
    STORE.track("contact_consent_given"); STORE.track("phone_submitted")
    session["state"]="completed"; session["consented_contact"]=True; save(user.id)
    lang=LANGUAGES.get(session.get("language"),"نامشخص"); goal=session.get("goal","نامشخص"); score=session.get("score",0)
    await message.reply_text(generate_attractive_report(user.first_name or "زبان‌آموز",lang,score,goal),reply_markup=ReplyKeyboardRemove(),parse_mode="HTML")
    admin=os.getenv("ADMIN_CHAT_ID","").strip()
    if admin:
        try:
            admin_id=int(admin)
            text=("🔥 <b>لید جدید آوا</b>\n" f"👤 {html.escape(user.first_name or '')} {html.escape(user.last_name or '')}\n"
                  f"یوزرنیم: @{html.escape(user.username) if user.username else 'ندارد'}\nشناسه: <code>{user.id}</code>\n"
                  f"شمارهٔ ارسالی با رضایت: <code>{html.escape(phone)}</code>\nزبان: {html.escape(lang)}\nنمره: {score}/10\nهدف: {html.escape(goal)}")
            await context.bot.send_message(chat_id=admin_id,text=text,parse_mode="HTML")
        except (ValueError, Exception): logger.exception("Could not notify admin")
    else: logger.info("ADMIN_CHAT_ID unset; consented contact retained locally only")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=_user(update); session=load(user.id) if user else None
    if not update.message: return
    text="برای شروع تعیین سطح، /start را بزنید." if not session else ("لطفاً گزینهٔ داخل پیام سؤال را انتخاب کنید." if session.get("state")=="quiz" else "لطفاً از دکمه‌های نمایش‌داده‌شده استفاده کنید.")
    await update.message.reply_text(text)

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user=_user(update); admin=os.getenv("ADMIN_CHAT_ID","").strip()
    if not user or not admin or str(user.id) != admin:
        await update.message.reply_text("این گزارش فقط برای مدیر پیکربندی‌شده در دسترس است."); return
    stats=STORE.summary()
    labels = [("bot_start","شروع بات"),("intent_selected","انتخاب نیت"),("quiz_started","شروع آزمون"),("quiz_completed","تکمیل آزمون"),("result_shown","نمایش نتیجه"),("contact_prompt_shown","نمایش درخواست تماس"),("contact_declined","رد تماس"),("help_in_telegram","انتخاب راهنمایی تلگرام (نه مشاورهٔ دریافت‌شده)"),("consultation_menu_shown","نمایش منوی مشاوره (کلیک/فرم قابل‌شمارش نیست)"),("contact_consent_given","رضایت/اشتراک مخاطب"),("phone_submitted","ارسال شماره"),("advisor_option_shown_start","نمایش دکمهٔ واتساپ مشاور در پیام /start (فقط نمایش؛ کلیک/گفت‌وگو قابل‌شمارش نیست)"),("advisor_option_shown_result","نمایش دکمهٔ واتساپ مشاور همراه نتیجه (فقط نمایش؛ کلیک/گفت‌وگو قابل‌شمارش نیست)")]
    lines = ["گزارش محلی SQLite (تعداد رویدادها؛ بدون شناسه/متن تماس در آمار قیف)", f"کاربران ذخیره‌شده: {stats['users']}", f"نتیجه‌های نمایش‌داده‌شده/تکمیل‌شده: {stats['completed']}", f"شماره‌های داوطلبانه: {stats['consented_contacts']}"]
    lines.extend(f"{label}: {stats[key]}" for key,label in labels)
    await update.message.reply_text("\n".join(lines))

def main():
    token=os.getenv("BOT_TOKEN","").strip()
    if not token: raise RuntimeError("BOT_TOKEN environment variable is required")
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("report",report_command))
    app.add_handler(CommandHandler("consultation",consultation_command))
    app.add_handler(CallbackQueryHandler(callback_handler))  # one callback handler; it routes all callback_data
    app.add_handler(MessageHandler(filters.CONTACT,contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    logger.info("Ava bot polling started")
    app.run_polling()

if __name__ == "__main__": main()
