from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

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
    await ask_exercise(update, context, update.message.chat_id)

async def ask_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    workout = context.user_data.get("workout")
    if not workout or workout["current_exercise_index"] >= len(workout["exercises"]):
        await finish_workout(update, context)
        return

    # Если chat_id не передан, определяем его из update
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

    keyboard = [[InlineKeyboardButton(f"{w} кг", callback_data=f"weight_{w}") for w in exercise["weights"]]]
    keyboard.append([InlineKeyboardButton("Пропустить упражнение", callback_data="skip_exercise")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🏋️‍♀️ *{exercise['name']}*\nВыбери вес:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def finish_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    results = context.user_data.get("workout", {}).get("results", [])
    if not results:
        await update.message.reply_text("❌ Нет данных о тренировке.")
        return
    text = "🏋️‍♀️ *Тренировка завершена!*\n\n📊 *Статистика:*\n"
    total_rest = 0
    for r in results:
        text += f"• {r['name']} — {r['weight']} кг х {r['reps']} х {r['sets']} (отдых {r['rest']} мин)\n"
        total_rest += r['rest']
    avg_rest = total_rest / len(results) if results else 0
    text += f"\n⏱️ *Средний отдых:* ≈ {avg_rest:.1f} мин"
    text += f"\n✅ Выполнено: {len(results)}/{len(context.user_data['workout']['exercises'])} упражнений"
    text += "\n💪 Молодец!"
    await update.message.reply_text(text, parse_mode="Markdown")
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
        await query.edit_message_text("⏩ Упражнение пропущено.")
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
            await finish_workout(update, context)
        else:
            await ask_exercise(update, context, chat_id)
        return
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏋️‍♀️ *Трекер тренировок*\n\n"
        "Команды:\n"
        "/workout — начать тренировку на сегодня\n"
        "/start — это сообщение",
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
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("test_workout", test_workout))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("Бот трекера тренировок запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()