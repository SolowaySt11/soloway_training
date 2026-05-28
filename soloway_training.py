from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

TOKEN = "8988046732:AAHeX1dCsfSw4hYwKT9NWk1roEU1lktNII8"

# ---------- ДАННЫЕ ТРЕНИРОВОК ----------
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
    "wednesday": {"name": "Руки + Плечи", "exercises": []},  # добавим позже
    "thursday": {"name": "Отдых", "exercises": []},
    "friday": {"name": "Ягодицы + Ноги", "exercises": []},  # пока те же, что в понедельник
    "saturday": {"name": "Отдых", "exercises": []},
    "sunday": {"name": "Грудь + Спина", "exercises": []}   # добавим позже
}

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
def get_today_workout():
    weekday = datetime.now().strftime("%A").lower()
    return WORKOUTS.get(weekday, {"name": "Нет тренировки", "exercises": []})

# ---------- КОМАНДА /WORKOUT ----------
async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    workout_data = get_today_workout()
    if not workout_data["exercises"]:
        await update.message.reply_text(f"Сегодня {workout_data['name']}. Отдыхай! 🛌")
        return
    
    # Сохраняем данные тренировки в user_data
    context.user_data["workout"] = {
        "name": workout_data["name"],
        "exercises": workout_data["exercises"].copy(),
        "results": [],
        "current_exercise_index": 0
    }
    await ask_exercise(update, context)

async def ask_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    workout = context.user_data.get("workout")
    if not workout or workout["current_exercise_index"] >= len(workout["exercises"]):
        await finish_workout(update, context)
        return
    
    exercise = workout["exercises"][workout["current_exercise_index"]]
    keyboard = [[InlineKeyboardButton(f"{w} кг", callback_data=f"weight_{w}") for w in exercise["weights"]]]
    keyboard.append([InlineKeyboardButton("Пропустить упражнение", callback_data="skip_exercise")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🏋️‍♀️ *{exercise['name']}*\nВыбери вес:",
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
        text += f"• {r['name']} — {r['sets']}х{r['weight']} кг (отдых {r['rest']} мин)\n"
        total_rest += r['rest']
    
    avg_rest = total_rest / len(results) if results else 0
    text += f"\n⏱️ *Средний отдых:* ≈ {avg_rest:.1f} мин"
    text += f"\n✅ Выполнено: {len(results)}/{len(context.user_data['workout']['exercises'])} упражнений"
    text += "\n💪 Молодец!"
    
    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data.pop("workout", None)

# ---------- ОБРАБОТЧИК КНОПОК ----------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    workout = context.user_data.get("workout")
    
    if not workout:
        await query.edit_message_text("Начни тренировку с /workout")
        return
    
    if data == "skip_exercise":
        workout["current_exercise_index"] += 1
        await query.edit_message_text("⏩ Упражнение пропущено.")
        await ask_exercise(update, context)
        return
    
    if data.startswith("weight_"):
        weight = int(data.split("_")[1])
        # Сохраняем выбранный вес, затем спрашиваем подходы
        workout["temp_weight"] = weight
        keyboard = [[InlineKeyboardButton(f"{s}", callback_data=f"sets_{s}") for s in [2,3,4,5]]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⚡ Вес: {weight} кг. Сколько подходов?",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("sets_"):
        sets = int(data.split("_")[1])
        workout["temp_sets"] = sets
        keyboard = [[InlineKeyboardButton(f"{r} мин", callback_data=f"rest_{r}") for r in [1, 1.5, 2]]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⏱️ {sets} подхода. Сколько минут отдыха между подходами?",
            reply_markup=reply_markup
        )
        return
    
    if data.startswith("rest_"):
        rest = float(data.split("_")[1])
        # Сохраняем результат упражнения
        exercise = workout["exercises"][workout["current_exercise_index"]]
        workout["results"].append({
            "name": exercise["name"],
            "weight": workout["temp_weight"],
            "sets": workout["temp_sets"],
            "rest": rest
        })
        workout["current_exercise_index"] += 1
        await query.edit_message_text("✅ Записано!")
        await ask_exercise(update, context)
        return

# ---------- ЗАПУСК ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏋️‍♀️ *Трекер тренировок*\n\n"
        "Команды:\n"
        "/workout — начать тренировку на сегодня\n"
        "/start — это сообщение",
        parse_mode="Markdown"
    )

#deletelater 
async def test_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Принудительно подставляем понедельник
    test_workout_data = WORKOUTS["monday"]
    context.user_data["workout"] = {
        "name": test_workout_data["name"],
        "exercises": test_workout_data["exercises"].copy(),
        "results": [],
        "current_exercise_index": 0
    }
    await ask_exercise(update, context)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(CommandHandler("test_workout", test_workout))
    print("Бот трекера тренировок запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()