import logging
import requests
import csv
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT, COMMAND

# Set up logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets URLs (CSV Format)
DECISION_POINTS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"
QUESTIONS_URL = "https://docs.google.com/spreadsheets/d/1YOUR_SHEET_ID/export?format=csv&gid=123456"  # Replace with actual GID for Questions

# Fetch data from Google Sheets
def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        decoded_content = response.content.decode("utf-8")
        data = list(csv.reader(decoded_content.splitlines(), delimiter=","))
        logger.info("Fetched data: %s", data)
        return data[1:]  # Skip header row
    except Exception as e:
        logger.error("Error fetching CSV data: %s", e)
        return []

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Handling /start from user: %s", update.effective_user.username)
    context.user_data['used_scenarios'] = set()
    context.user_data['score'] = 0
    context.user_data['time'] = 0
    context.user_data['prestige_stars'] = 0

    welcome_message = (
        "🎮 **Chào mừng bạn đến với GameFi Nhập Vai!** 🎉\n\n"
        "Bạn sẽ bước vào một hành trình phiêu lưu đầy thách thức.\n"
        "⏩ Gõ /play để bắt đầu hành trình của bạn!"
    )
    if update.message:
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

# /play command handler
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    decision_points = fetch_csv_data(DECISION_POINTS_URL)
    if not decision_points:
        if update.message:
            await update.message.reply_text("❌ Không thể tải dữ liệu trò chơi. Vui lòng thử lại sau.")
        return

    # Randomly select a scenario that hasn't been used yet
    unused_scenarios = [p for p in decision_points if p[0] not in context.user_data['used_scenarios']]
    if not unused_scenarios:
        await summarize_game(update, context)
        return

    point = random.choice(unused_scenarios)
    context.user_data['used_scenarios'].add(point[0])  # Mark scenario as used

    scenario = point[0]
    option_1 = point[1]
    option_2 = point[3]

    # Save the current scenario
    context.user_data['current_scenario'] = {
        "scenario": scenario,
        "option_1": option_1,
        "time_1": int(point[2]),
        "option_2": option_2,
        "time_2": int(point[4]),
        "prestige_star": point[5] if len(point) > 5 else None,
    }

    message = (
        f"🗺️ *{scenario}*\n\n"
        f"1️⃣ {option_1}\n"
        f"2️⃣ {option_2}\n\n"
        f"⏩ Nhập số 1 hoặc 2 để chọn."
    )
    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")

# Handle user choices
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text
    current_scenario = context.user_data.get('current_scenario', None)

    if not current_scenario or user_choice not in ['1', '2']:
        if update.message:
            await update.message.reply_text("❌ Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")
        return

    choice_key = 'option_1' if user_choice == '1' else 'option_2'
    time_key = 'time_1' if user_choice == '1' else 'time_2'

    chosen_option = current_scenario[choice_key]
    time_cost = current_scenario[time_key]
    prestige_star = current_scenario['prestige_star']

    # Update user stats
    context.user_data['time'] += time_cost
    if prestige_star and prestige_star == f"Option {user_choice}":
        context.user_data['prestige_stars'] += 1

    response = (
        f"✅ Bạn đã chọn: {chosen_option}\n"
        f"⏱️ Thời gian bạn cần để hoàn thành việc này là: {time_cost} giây.\n"
        f"⏱️ Tổng thời gian chơi của bạn đến giờ là: {context.user_data['time']} giây.\n"
        f"🌟 Tổng Ngôi sao danh giá của bạn là: {context.user_data['prestige_stars']}."
    )
    if update.message:
        await update.message.reply_text(response)

    # Fetch and present a question after the decision point
    await ask_question(update, context)

# Fetch and present a random question
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = fetch_csv_data(QUESTIONS_URL)
    if not questions:
        if update.message:
            await update.message.reply_text("❌ Không thể tải câu hỏi. Vui lòng thử lại sau.")
        return

    question = random.choice(questions)  # Randomly select a question
    question_text = question[0]
    options = question[1:4]
    correct_answer = question[4]

    # Save the correct answer for validation
    context.user_data['current_question'] = {
        "question_text": question_text,
        "options": options,
        "correct_answer": correct_answer,
    }

    message = (
        f"🤔 *Câu hỏi:* {question_text}\n\n"
        f"1️⃣ {options[0]}\n"
        f"2️⃣ {options[1]}\n"
        f"3️⃣ {options[2]}\n\n"
        f"⏩ Nhập số 1, 2 hoặc 3 để trả lời."
    )
    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")

# Summarize the game
async def summarize_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time = context.user_data.get('time', 0)
    prestige_stars = context.user_data.get('prestige_stars', 0)

    summary = (
        f"🎉 **Hành trình của bạn đã kết thúc!** 🎉\n\n"
        f"⏳ *Tổng thời gian:* **{time} giây**\n"
        f"🌟 *Ngôi sao danh giá:* **{prestige_stars}**\n\n"
        f"✨ **Cảm ơn bạn đã tham gia GameFi Nhập Vai!** ✨"
    )
    if update.message:
        await update.message.reply_text(summary, parse_mode="Markdown")

# Main function
def main():
    TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
    application = Application.builder().token(TOKEN).build()

    logger.info("Bot is starting with token: %s", TOKEN)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(MessageHandler(TEXT & ~COMMAND, handle_choice))

    application.run_polling()

if __name__ == "__main__":
    logger.info("Bot is initializing...")
    main()
