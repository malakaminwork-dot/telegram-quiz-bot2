import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
import db
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL") + WEBHOOK_PATH

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
app = FastAPI()

user_answers = {}
current_question = {}


@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("👋 أهلاً بك\n/add_question\n/start_exam\n/result")


# ===== المعلم =====
@dp.message(Command("add_question"))
async def add_q(msg: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="صح / خطأ", callback_data="tf")],
        [InlineKeyboardButton(text="اختيارات", callback_data="mcq")]
    ])
    await msg.answer("اختر نوع السؤال:", reply_markup=kb)


@dp.callback_query(lambda c: c.data in ["tf", "mcq"])
async def q_type(call: types.CallbackQuery):
    current_question[call.from_user.id] = {"type": call.data}
    await call.message.answer("📷 أرسل صورة السؤال")
    await call.answer()


@dp.message(lambda m: m.photo)
async def get_image(msg: types.Message):
    uid = msg.from_user.id
    if uid not in current_question:
        return

    current_question[uid]["image"] = msg.photo[-1].file_id

    if current_question[uid]["type"] == "tf":
        await msg.answer("أرسل الإجابة الصحيحة (صح / خطأ)")
    else:
        await msg.answer("أرسل الاختيارات مفصولة بفاصلة")


@dp.message()
async def save_question(msg: types.Message):
    uid = msg.from_user.id
    if uid not in current_question:
        return

    q = current_question[uid]

    if q["type"] == "tf":
        db.add_question("tf", q["image"], msg.text.strip())
        await msg.answer("✅ تم حفظ السؤال")
        current_question.pop(uid)

    elif "choices" not in q:
        q["choices"] = [c.strip() for c in msg.text.split(",")]
        await msg.answer("أرسل الإجابة الصحيحة")

    else:
        db.add_question("mcq", q["image"], msg.text.strip(), q["choices"])
        await msg.answer("✅ تم حفظ السؤال")
        current_question.pop(uid)


# ===== الطالب =====
@dp.message(Command("start_exam"))
async def exam(msg: types.Message):
    qs = db.get_questions()
    user_answers[msg.from_user.id] = {"score": 0, "total": len(qs)}

    for q in qs:
        q_id, q_type, img, correct = q

        if q_type == "tf":
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="صح", callback_data=f"{q_id}:صح"),
                InlineKeyboardButton(text="خطأ", callback_data=f"{q_id}:خطأ")
            ]])
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=c, callback_data=f"{q_id}:{c}")]
                for c in db.get_choices(q_id)
            ])

        await bot.send_photo(msg.chat.id, img, reply_markup=kb)


@dp.callback_query(lambda c: ":" in c.data)
async def answer(call: types.CallbackQuery):
    q_id, ans = call.data.split(":")
    q_id = int(q_id)

    for q in db.get_questions():
        if q[0] == q_id and q[3] == ans:
            user_answers[call.from_user.id]["score"] += 1

    await call.answer("تم تسجيل الإجابة ✅")


@dp.message(Command("result"))
async def result(msg: types.Message):
    r = user_answers.get(msg.from_user.id)
    if not r:
        await msg.answer("❌ لم تدخل اختبار")
        return
    await msg.answer(f"📊 نتيجتك:\n{r['score']} / {r['total']}")


# ===== Webhook =====
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()


app.add_api_route(
    WEBHOOK_PATH,
    SimpleRequestHandler(dp, bot),
    methods=["POST"]
)
