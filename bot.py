import logging
import requests
import csv
import random
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT, COMMAND

# Logging setup
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets URLs
DECISION_POINTS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"
QUESTIONS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=1301413371"

# Fetch data from Google Sheets
def fetch_csv_data(url, tab_name):
    try:
        logger.info(f"Fetching data from {tab_name} at {url}")
        response = requests.get(url)
        response.raise_for_status()
        decoded_content = response.content.decode("utf-8")
        data = list(csv.reader(decoded_content.splitlines(), delimiter=","))
        return data[1:]  # Skip header
    except Exception as e:
        logger.error(f"Error fetching data from {tab_name}: {e}")
        return []

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['used_scenarios'] = set()
    context.user_data['used_questions'] = set()
    context.user_data['score'] = 0
    context.user_data['time'] = 0
    context.user_data['prestige_stars'] = 0
    context.user_data['round'] = 0

    welcome_message = (
        "🎮 **Chào mừng bạn đến với GameFi Nhập Vai!** 🎉\n\n"
        "⏩ Gõ /play để bắt đầu hành trình của bạn!"
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# /play command
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['round'] >= 10:
        await summarize_game(update, context)
        return

    # Alternate between scenario and question
    if context.user_data['round'] % 2 == 0:
        await play_scenario(update, context)
    else:
        await ask_question(update, context)

async def play_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    decision_points = fetch_csv_data(DECISION_POINTS_URL, "Decision Points")
    if not decision_points:
        await update.message.reply_text("❌ Không thể tải dữ liệu trò chơi. Vui lòng thử lại sau.")
        return

    unused_scenarios = [p for p in decision_points if p[0] not in context.user_data['used_scenarios']]
    if not unused_scenarios:
        await summarize_game(update, context)
        return

    point = random.choice(unused_scenarios)
    context.user_data['used_scenarios'].add(point[0])
    context.user_data['current_scenario'] = {
        "scenario": point[0],
        "option_1": point[1],
        "time_1": int(point[2]),
        "option_2": point[3],
        "time_2": int(point[4]),
        "prestige_star": point[5] if len(point) > 5 else None,
    }

    round_number = context.user_data['round'] // 2 + 1
    message = (
        f"🗺️ *Câu {round_number} - Scenario:* {point[0]}\n\n"
        f"1️⃣ {point[1]}\n"
        f"2️⃣ {point[3]}\n\n"
        f"⏩ Nhập số 1 hoặc 2 để chọn."
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text
    current_scenario = context.user_data.get('current_scenario', None)

    if not current_scenario or user_choice not in ['1', '2']:
        await update.message.reply_text("❌ Vui lòng nhập 1 hoặc 2.")
        return

    choice_key = 'option_1' if user_choice == '1' else 'option_2'
    time_key = 'time_1' if user_choice == '1' else 'time_2'

    chosen_option = current_scenario[choice_key]
    time_cost = current_scenario[time_key]
    prestige_star = current_scenario['prestige_star']

    context.user_data['time'] += time_cost
    if prestige_star and prestige_star == f"Option {user_choice}":
        context.user_data['prestige_stars'] += 1

    response = (
        f"✅ Bạn đã chọn: {chosen_option}\n"
        f"⏱️ Thời gian thêm: {time_cost} giây.\n"
        f"🌟 Tổng Ngôi sao danh giá: {context.user_data['prestige_stars']}\n"
        f"🎯 Tổng thời gian hiện tại: {context.user_data['time']} giây."
    )
    await update.message.reply_text(response)

    context.user_data['round'] += 1
    await play(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = fetch_csv_data(QUESTIONS_URL, "Questions")
    if not questions:
        await update.message.reply_text("❌ Không thể tải câu hỏi.")
        return

    unused_questions = [q for q in questions if q[0] not in context.user_data['used_questions']]
    if not unused_questions:
        await summarize_game(update, context)
        return

    question = random.choice(unused_questions)
    context.user_data['used_questions'].add(question[0])
    context.user_data['current_question'] = {
        "question_text": question[0],
        "options": question[1:4],
        "correct_answer": str(question[4]),  # Ensure correct_answer is a string
        "score": 10,  # Fix score to 10 points per correct answer
        "start_time": time.time(),
    }

    round_number = context.user_data['round'] // 2 + 1
    message = (
        f"🤔 *Câu {round_number} - Question:* {question[0]}\n\n"
        f"1️⃣ {question[1]}\n"
        f"2️⃣ {question[2]}\n"
        f"3️⃣ {question[3]}\n\n"
        f"⏩ Nhập số 1, 2 hoặc 3 để trả lời."
    )
    await update.message.reply_text(message, parse_mode="Markdown")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text
    current_question = context.user_data.get('current_question', None)

    if not current_question or user_choice not in ['1', '2', '3']:
        await update.message.reply_text("❌ Vui lòng nhập 1, 2 hoặc 3.")
        return

    end_time = time.time()
    answer_time = int(end_time - current_question['start_time'])
    context.user_data['time'] += answer_time

    try:
        chosen_option = current_question['options'][int(user_choice) - 1]
        correct_answer = current_question['correct_answer']
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Đã xảy ra lỗi trong quá trình xử lý câu trả lời. Vui lòng thử lại.")
        return

    if user_choice == correct_answer:
        context.user_data['score'] += current_question['score']
        response = (
            f"✅ Bạn đã chọn: {chosen_option}\n"
            f"🏆 Điểm cộng: {current_question['score']}\n"
            f"⏱️ Thời gian trả lời: {answer_time} giây.\n"
            f"🎯 Tổng điểm: {context.user_data['score']}\n"
            f"⏳ Tổng thời gian hiện tại: {context.user_data['time']} giây."
        )
    else:
        response = (
            f"❌ Bạn đã chọn: {chosen_option}\n"
            f"⏱️ Thời gian trả lời: {answer_time} giây.\n"
            f"🎯 Tổng điểm: {context.user_data['score']}\n"
            f"⏳ Tổng thời gian hiện tại: {context.user_data['time']} giây."
        )

    await update.message.reply_text(response)
    context.user_data['round'] += 1
    await play(update, context)

async def summarize_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    score = context.user_data.get('score', 0)
    time = context.user_data.get('time', 0)
    prestige_stars = context.user_data.get('prestige_stars', 0)

    summary = (
        f"🎉 **Kết thúc trò chơi!** 🎉\n\n"
        f"⏳ Thời gian: **{time} giây**\n"
        f"🏆 Điểm số: **{score}**\n"
        f"🌟 Ngôi sao danh giá: **{prestige_stars}**\n\n"
        f"✨ Cảm ơn bạn đã tham gia!"
    )
    await update.message.reply_text(summary, parse_mode="Markdown")

# Run bot
def main():
    TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(MessageHandler(TEXT & ~COMMAND, handle_choice))
    application.add_handler(MessageHandler(TEXT & ~COMMAND, handle_answer))

    application.run_polling()

if __name__ == "__main__":
    main()
