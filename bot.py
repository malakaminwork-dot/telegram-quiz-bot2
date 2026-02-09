from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor

from config import BOT_TOKEN
import db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

user_answers = {}
current_question = {}


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer(
        "👋 أهلاً بك\n"
        "/add_question ➜ للمعلم\n"
        "/start_exam ➜ للطالب"
    )


# ====== المعلم ======
@dp.message_handler(commands=["add_question"])
async def add_q(msg: types.Message):
    await msg.answer(
        "اختر نوع السؤال:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("✔️ صح / خطأ", callback_data="tf"),
            InlineKeyboardButton("🔘 اختيارات", callback_data="mcq")
        )
    )


@dp.callback_query_handler(lambda c: c.data in ["tf", "mcq"])
async def q_type(call: types.CallbackQuery):
    current_question[call.from_user.id] = {"type": call.data}
    await call.message.answer("📷 أرسل صورة السؤال")


@dp.message_handler(content_types=["photo"])
async def get_image(msg: types.Message):
    uid = msg.from_user.id
    if uid not in current_question:
        return

    current_question[uid]["image"] = msg.photo[-1].file_id

    if current_question[uid]["type"] == "tf":
        await msg.answer("أرسل الإجابة الصحيحة: (صح / خطأ)")
    else:
        await msg.answer(
            "أرسل الاختيارات مفصولة بفاصلة\nمثال:\nA,B,C,D"
        )


@dp.message_handler()
async def save_question(msg: types.Message):
    uid = msg.from_user.id
    if uid not in current_question:
        return

    q = current_question[uid]

    if q["type"] == "tf":
        db.add_question("tf", q["image"], msg.text)
        await msg.answer("✅ تم حفظ السؤال")
        current_question.pop(uid)

    else:
        choices = msg.text.split(",")
        await msg.answer("أرسل الإجابة الصحيحة")
        q["choices"] = choices
        q["step"] = "answer"


@dp.message_handler()
async def save_mcq_answer(msg: types.Message):
    uid = msg.from_user.id
    if uid not in current_question:
        return

    q = current_question[uid]
    if q.get("step") == "answer":
        db.add_question("mcq", q["image"], msg.text, q["choices"])
        await msg.answer("✅ تم حفظ السؤال")
        current_question.pop(uid)


# ====== الطالب ======
@dp.message_handler(commands=["start_exam"])
async def exam(msg: types.Message):
    questions = db.get_questions()
    user_answers[msg.from_user.id] = {"score": 0, "total": len(questions)}

    for q in questions:
        q_id, q_type, img, correct = q

        if q_type == "tf":
            kb = InlineKeyboardMarkup().add(
                InlineKeyboardButton("صح", callback_data=f"{q_id}:صح"),
                InlineKeyboardButton("خطأ", callback_data=f"{q_id}:خطأ")
            )
        else:
            kb = InlineKeyboardMarkup()
            for c in db.get_choices(q_id):
                kb.add(InlineKeyboardButton(c, callback_data=f"{q_id}:{c}"))

        await bot.send_photo(msg.chat.id, img, reply_markup=kb)


@dp.callback_query_handler(lambda c: ":" in c.data)
async def answer(call: types.CallbackQuery):
    q_id, ans = call.data.split(":")
    q_id = int(q_id)

    for q in db.get_questions():
        if q[0] == q_id:
            if ans == q[3]:
                user_answers[call.from_user.id]["score"] += 1

    await call.answer("تم تسجيل الإجابة")


@dp.message_handler(commands=["result"])
async def result(msg: types.Message):
    r = user_answers.get(msg.from_user.id)
    if not r:
        await msg.answer("❌ لم تدخل اختبار")
        return

    await msg.answer(
        f"📊 نتيجتك:\n"
        f"{r['score']} / {r['total']}"
    )


if __name__ == "__main__":
    executor.start_polling(dp)
