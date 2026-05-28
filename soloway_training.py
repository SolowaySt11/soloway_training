from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime, timedelta
import random
import sqlite3
import os

TOKEN = "8988046732:AAHeX1dCsfSw4hYwKT9NWk1roEU1lktNII8"

WORKOUTS = {
    "monday": {
        "name": "Ягодицы + Ноги",
        "exercises": [
            {"name": "Приседания со штангой", "weights": [15, 20, 25]},
            {"name": "Румынская тяга", "weights": [15, 20, 25]},
            {"name": "Ягодичный мостик", "weights": [15, 20, 25]},
            {"name": "Выпады (румынские)", "weights": [10, 16]},
            {"name": "Подъёмы икр", "weights": [15, 20, 25]},
            {"name": "Гиперэкстензия", "weights": [4, 8, 10]}
        ]
    },
    "tuesday": {"name": "Отдых", "exercises": []},
    "wednesday": {
        "name": "Руки + Плечи",
        "exercises": [
            {"name": "Подъём штанги на бицепс", "weights": [10, 12.5, 15]},
            {"name": "Отжимания с отягощением / брусья", "weights": [5, 10, 15]},
            {"name": "Жим гантелей вверх", "weights": [6, 8, 12]},
            {"name": "Разводка гантелей", "weights": [4, 6, 8]},
            {"name": "Молотки", "weights": [8, 16]}
        ]
    },
    "thursday": {"name": "Отдых", "exercises": []},
    "friday": {"name": "Ягодицы + Ноги", "exercises": []},
    "saturday": {"name": "Отдых", "exercises": []},
    "sunday": {
        "name": "Грудь + Спина",
        "exercises": [
            {"name": "Отжимания", "weights": [2, 4]},
            {"name": "Жим лёжа", "weights": [15, 20, 25]},
            {"name": "Тяга штанги в наклоне", "weights": [12.5, 15, 20]},
            {"name": "Тяга обратным хватом", "weights": [12.5, 15, 20]},
            {"name": "Бабочка с гантелями", "weights": [4, 6, 8]},
            {"name": "Австралийские подтягивания", "weights": []},
            {"name": "Шраги", "weights": [15, 20, 25]}
        ]
    }
}

encouragements = [
    "🔥 Сэр, вы в отличной форме!",
    "💪 Ещё один шаг к идеалу. Записываю.",
    "🎯 Сосредоточьтесь. Техника решает всё.",
    "⚡ Легко? Тогда в следующий раз возьмите больше вес.",
    "🤖 Джарвис на связи. Продолжаем.",
    "🏆 Вы сильнее, чем думаете, сэр.",
    "📈 Ещё подход — и прогресс будет виден.",
    "🎧 Работаем. Без музыки, но с характером."
]

# --- База данных ---
def init_db():
    conn = sqlite3.connect("training.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            exercise TEXT,
            weight REAL,
            reps INTEGER,
            sets INTEGER,
            rest REAL
        )
    """)
    conn.commit()
    conn.close()

def save_workout(user_id, date, exercise, weight, reps, sets, rest):
    conn = sqlite3.connect("training.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO workouts (user_id, date, exercise, weight, reps, sets, rest)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, date, exercise, weight, reps, sets, rest))
    conn.commit()
    conn.close()

def get_report(user_id, days=30):
    conn = sqlite3.connect("training.db")
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("""
        SELECT date, exercise, weight, reps, sets, rest
        FROM workouts
        WHERE user_id = ? AND date >= ?
        ORDER BY date ASC
    """, (user_id, cutoff))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Основные функции бота ---
def get_today_workout():
    weekday = datetime.now().strftime("%A").lower()
    return WORKOUTS.get(weekday, {"name": "Нет тренировки", "exercises": []})

async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    workout_data = get_today_workout()
    if not workout_data["exercises"]:
        await update.message.reply_text(f"Сегодня {workout_data['name']}. Отдыхай! 🛌")
        return
    context.user_data["workout"] = {
        "name": workout_data["name"],
        "exercises": workout_data["exercises"].copy(),
        "results": [],
        "current_exercise_index": 0
    }
    await update.message.reply_text("🏋️‍♂️ Сэр, вы готовы к тренировке? Я записал план. Поехали.")
    await ask_exercise(update, context, update.message.chat_id)

async def ask_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    workout = context.user_data.get("workout")
    if not workout or workout["current_exercise_index"] >= len(workout["exercises"]):
        await finish_workout(update, context, chat_id)
        return

    if chat_id is None:
        if update.message:
            chat_id = update.message.chat_id
        elif update.callback_query:
            chat_id = update.callback_query.message.chat_id
        else:
            return

    exercise = workout["exercises"][workout["current_exercise_index"]]
    if not exercise["weights"]:
        workout["results"].append({
            "name": exercise["name"],
            "weight": 0,
            "reps": 0,
            "sets": 0,
            "rest": 0
        })
        workout["current_exercise_index"] += 1
        await context.bot.send_message(chat_id=chat_id, text=f"✅ {exercise['name']} (без веса) — пропущено")
        await ask_exercise(update, context, chat_id)
        return

    phrase = random.choice(encouragements)
    keyboard = [[InlineKeyboardButton(f"{w} кг", callback_data=f"weight_{w}") for w in exercise["weights"]]]
    keyboard.append([InlineKeyboardButton("Пропустить упражнение", callback_data="skip_exercise")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🏋️‍♀️ *{exercise['name']}*\n{phrase}\nВыбери вес:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def finish_workout(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    workout = context.user_data.get("workout")
    if not workout:
        return

    results = workout.get("results", [])
    if not results:
        context.user_data.pop("workout", None)
        return

    if chat_id is None:
        if update.message:
            chat_id = update.message.chat_id
        elif update.callback_query:
            chat_id = update.callback_query.message.chat_id
        else:
            return

    user_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")

    # Сохраняем каждое упражнение в базу
    for r in results:
        save_workout(user_id, today, r['name'], r['weight'], r['reps'], r['sets'], r['rest'])

    # Текст статистики
    text = "🏋️‍♀️ *Тренировка завершена!*\n\n📊 *Статистика:*\n"
    total_rest = 0
    for r in results:
        text += f"• {r['name']} — {r['weight']} кг х {r['reps']} х {r['sets']} (отдых {r['rest']} мин)\n"
        total_rest += r['rest']

    avg_rest = total_rest / len(results) if results else 0
    text += f"\n⏱️ *Средний отдых:* ≈ {avg_rest:.1f} мин"
    text += f"\n✅ Выполнено: {len(results)}/{len(workout['exercises'])} упражнений"
    text += "\n\n🏆 Отличная работа, сэр. Ваше тело становится крепче. 💪"

    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    context.user_data.pop("workout", None)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id
    workout = context.user_data.get("workout")
    
    if not workout:
        await query.edit_message_text("Начни тренировку с /workout")
        return

    if data == "skip_exercise":
        workout["current_exercise_index"] += 1
        await query.edit_message_text("⏩ Упражнение пропущено. Но я всё равно в вас верю, сэр.")
        await ask_exercise(update, context, chat_id)
        return

    if data.startswith("weight_"):
        weight = float(data.split("_")[1])
        workout["temp_weight"] = weight
        keyboard = [[InlineKeyboardButton(f"{r}", callback_data=f"reps_{r}") for r in [6,8,10,12,15]]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚡ Вес: {weight} кг. Сколько повторений?",
            reply_markup=reply_markup
        )
        return

    if data.startswith("reps_"):
        reps = int(data.split("_")[1])
        workout["temp_reps"] = reps
        keyboard = [[InlineKeyboardButton(f"{s}", callback_data=f"sets_{s}") for s in [2,3,4,5]]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"💪 {reps} повторений. Сколько подходов?",
            reply_markup=reply_markup
        )
        return

    if data.startswith("sets_"):
        sets = int(data.split("_")[1])
        workout["temp_sets"] = sets
        keyboard = [[InlineKeyboardButton(f"{r} мин", callback_data=f"rest_{r}") for r in [1, 1.5, 2]]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"🏋️‍♀️ {sets} подхода. Сколько минут отдыха?",
            reply_markup=reply_markup
        )
        return

    if data.startswith("rest_"):
        rest = float(data.split("_")[1])
        exercise = workout["exercises"][workout["current_exercise_index"]]
        workout["results"].append({
            "name": exercise["name"],
            "weight": workout["temp_weight"],
            "reps": workout["temp_reps"],
            "sets": workout["temp_sets"],
            "rest": rest
        })
        workout["current_exercise_index"] += 1
        await query.edit_message_text("✅ Записано!")
        
        if workout["current_exercise_index"] >= len(workout["exercises"]):
            await finish_workout(update, context, chat_id)
        else:
            await ask_exercise(update, context, chat_id)
        return

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    rows = get_report(user_id, days=30)

    if not rows:
        await update.message.reply_text("📊 За последние 30 дней нет данных. Проведите тренировку и повторите команду.")
        return

    # Группируем по упражнениям
    exercises = {}
    for row in rows:
        date, ex, weight, reps, sets, rest = row
        if ex not in exercises:
            exercises[ex] = []
        exercises[ex].append({"weight": weight, "reps": reps, "sets": sets, "date": date})

    text = "📊 *Отчёт за 30 дней*\n\n"
    text += f"🏋️‍♀️ *Всего тренировок:* {len(set(r[0] for r in rows))}\n\n"

    for ex, data in exercises.items():
        # Средние значения
        avg_weight = sum(d["weight"] for d in data) / len(data)
        avg_reps = sum(d["reps"] for d in data) / len(data)
        avg_sets = sum(d["sets"] for d in data) / len(data)
        # Динамика: первый и последний вес
        first_weight = data[0]["weight"]
        last_weight = data[-1]["weight"]
        diff = last_weight - first_weight
        if diff > 0:
            trend = f"📈 +{diff} кг"
        elif diff < 0:
            trend = f"📉 {diff} кг"
        else:
            trend = "➡️ без изменений"

        text += f"*{ex}*\n"
        text += f"   🔹 Средний вес: {avg_weight:.1f} кг\n"
        text += f"   🔸 Средние повторения: {avg_reps:.1f}\n"
        text += f"   🔹 Средние подходы: {avg_sets:.1f}\n"
        text += f"   📊 Динамика: {trend}\n\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏋️‍♀️ *Джарвис Трекер*\n\n"
        "Команды:\n"
        "/workout — начать тренировку на сегодня\n"
        "/report — отчёт за 30 дней\n"
        "/start — это сообщение\n\n"
        "🤖 Джарвис поможет вам не сойти с пути силы.",
        parse_mode="Markdown"
    )

async def test_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_workout_data = WORKOUTS["monday"]
    context.user_data["workout"] = {
        "name": test_workout_data["name"],
        "exercises": test_workout_data["exercises"].copy(),
        "results": [],
        "current_exercise_index": 0
    }
    await ask_exercise(update, context, update.message.chat_id)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("test_workout", test_workout))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("Джарвис Трекер с SQLite запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()