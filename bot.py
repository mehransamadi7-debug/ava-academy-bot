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

class Store:
    """Small SQLite persistence layer. Replacing a user's snapshot is an atomic transaction."""
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, session_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    def put(self, user_id: int, session: dict[str, Any]) -> None:
        payload = json.dumps(session, ensure_ascii=False)
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM users WHERE user_id=?", (int(user_id),))
            db.execute("INSERT INTO users(user_id, session_json, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (int(user_id), payload))
    def get(self, user_id: int) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT session_json FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        return json.loads(row[0]) if row else None
    def summary(self) -> dict[str, int]:
        with sqlite3.connect(self.path) as db:
            total, completed, leads = db.execute("SELECT COUNT(*), SUM(CASE WHEN json_extract(session_json,'$.state')='completed' THEN 1 ELSE 0 END), SUM(CASE WHEN json_extract(session_json,'$.consented_contact')=1 THEN 1 ELSE 0 END) FROM users").fetchone()
        return {"users": total or 0, "completed": completed or 0, "consented_contacts": leads or 0}

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

def _user(update: Update):
    return update.effective_user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _user(update)
    if not user or not update.message: return
    user_sessions[user.id] = {"state":"choosing_language", "score":0, "question_index":0}
    save(user.id)
    kb = [[InlineKeyboardButton("🇬🇧 انگلیسی",callback_data="lang:en"),InlineKeyboardButton("🇩🇪 آلمانی",callback_data="lang:de")],
          [InlineKeyboardButton("🇫🇷 فرانسه",callback_data="lang:fr"),InlineKeyboardButton("🇮🇹 ایتالیایی",callback_data="lang:it")]]
    await update.message.reply_text(f"سلام {html.escape(user.first_name or 'دوست عزیز')}! به <b>آکادمی زبان آوا</b> خوش آمدید.\nاین آزمون کوتاه آموزشی است و نتیجهٔ آن گواهی رسمی CEFR نیست.\n\nزبان موردنظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

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
    if data.startswith("lang:"):
        language = data.partition(":")[2]
        if language not in QUESTIONS:
            await query.answer("زبان نامعتبر است.", show_alert=True); return
        user_sessions[user_id] = {"state":"quiz","language":language,"score":0,"question_index":0}
        save(user_id); await query.answer()
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
            session["state"]="awaiting_goal"; save(user_id)
            kb=[[InlineKeyboardButton(label,callback_data=key)] for key,label in GOALS.items()]
            await context.bot.send_message(chat_id=query.message.chat_id,text="آزمون تمام شد. هدف یادگیری خود را انتخاب کنید:",reply_markup=InlineKeyboardMarkup(kb));
        return
    if data in GOALS:
        if not session or session.get("state") != "awaiting_goal":
            await query.answer("لطفاً با /start آغاز کنید.",show_alert=True); return
        session["goal"]=GOALS[data]; session["state"]="awaiting_contact"; save(user_id)
        await query.answer(); await query.edit_message_reply_markup(reply_markup=None)
        kb=ReplyKeyboardMarkup([[KeyboardButton("📱 شماره‌ام را با رضایت ارسال می‌کنم",request_contact=True)]],resize_keyboard=True,one_time_keyboard=True)
        ikb=InlineKeyboardMarkup([[InlineKeyboardButton("بدون ارائهٔ شماره، دریافت گزارش",callback_data="contact_skip")]])
        await context.bot.send_message(chat_id=query.message.chat_id,text="گزارش شما آماده است. ارسال شماره کاملاً اختیاری است؛ فقط با لمس دکمهٔ اشتراک‌گذاری مخاطب، شماره برای پیگیری به آوا ارسال می‌شود. می‌توانید بدون شماره گزارش را دریافت کنید.",reply_markup=kb)
        await context.bot.send_message(chat_id=query.message.chat_id,text="انتخاب کنید:",reply_markup=ikb); return
    if data == "contact_skip":
        if not session or session.get("state") != "awaiting_contact":
            await query.answer("این مرحله فعال نیست.",show_alert=True); return
        session["state"]="completed"; session["consented_contact"]=False; save(user_id)
        await query.answer(); await query.edit_message_reply_markup(reply_markup=None)
        lang=LANGUAGES.get(session.get("language"),"نامشخص")
        await context.bot.send_message(chat_id=query.message.chat_id,text=generate_attractive_report(query.from_user.first_name or "زبان‌آموز",lang,session.get("score",0),session.get("goal","نامشخص")),parse_mode="HTML",reply_markup=ReplyKeyboardRemove()); return
    await query.answer("درخواست نامعتبر است.", show_alert=True)

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user= _user(update); message=update.message
    if not user or not message or not message.contact: return
    session=load(user.id)
    if not session or session.get("state") != "awaiting_contact":
        await message.reply_text("برای شروع، /start را ارسال کنید.",reply_markup=ReplyKeyboardRemove()); return
    contact=message.contact
    if contact.user_id is not None and contact.user_id != user.id:
        await message.reply_text("لطفاً فقط شمارهٔ خودتان را با رضایت ارسال کنید.",reply_markup=ReplyKeyboardRemove()); return
    phone=contact.phone_number
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
    await update.message.reply_text(f"گزارش محلی SQLite\nکاربران: {stats['users']}\nتکمیل‌شده: {stats['completed']}\nشماره‌های داوطلبانه: {stats['consented_contacts']}")

def main():
    token=os.getenv("BOT_TOKEN","").strip()
    if not token: raise RuntimeError("متغیر BOT_TOKEN تنظیم نشده است.")
    app=Application.builder().token(token).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("report",report_command))
    app.add_handler(CallbackQueryHandler(callback_handler))  # one callback handler; it routes all callback_data
    app.add_handler(MessageHandler(filters.CONTACT,contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    logger.info("Ava bot polling started")
    app.run_polling()

if __name__ == "__main__": main()
