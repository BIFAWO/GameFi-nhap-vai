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
def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        decoded_content = response.content.decode("utf-8")
        data = list(csv.reader(decoded_content.splitlines(), delimiter=","))
        return data[1:]  # Skip header
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return []

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['used_scenarios'] = set()
    context.user_data['used_questions'] = set()
    context.user_data['score'] = 0
    context.user_data['time'] = 0
    context.user_data['scenario_round'] = 0
    context.user_data['question_round'] = 0

    await update.message.reply_text(
        "🎮 **Chào mừng bạn đến với GameFi Nhập Vai!** 🎉\n\n"
        "⏩ Gõ /play để bắt đầu hành trình của bạn!",
        parse_mode="Markdown"
    )

# /play command
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_rounds = context.user_data['scenario_round'] + context.user_data['question_round']
    if total_rounds >= 10:
        await summarize_game(update, context)
        return

    if context.user_data['scenario_round'] <= context.user_data['question_round']:
        await play_scenario(update, context)
    else:
        await ask_question(update, context)

# Handle scenario
async def play_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scenarios = fetch_csv_data(DECISION_POINTS_URL)
    if not scenarios:
        await update.message.reply_text("❌ Không thể tải dữ liệu kịch bản. Vui lòng thử lại sau.")
        return

    unused_scenarios = [s for s in scenarios if s[0] not in context.user_data['used_scenarios']]
    if not unused_scenarios:
        await summarize_game(update, context)
        return

    scenario = random.choice(unused_scenarios)
    context.user_data['used_scenarios'].add(scenario[0])
    context.user_data['current_scenario'] = scenario
    context.user_data['scenario_round'] += 1

    await update.message.reply_text(
        f"🗺️ *Câu {context.user_data['scenario_round']} - Kịch bản:*\n\n"
        f"{scenario[0]}\n\n"
        f"1️⃣ {scenario[1]}\n"
        f"2️⃣ {scenario[3]}\n\n"
        "⏩ Nhập 1 hoặc 2 để chọn.",
        parse_mode="Markdown"
    )

# Handle choice
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip()
    current_scenario = context.user_data.get('current_scenario')

    if not current_scenario or user_choice not in ['1', '2']:
        await update.message.reply_text("❌ Vui lòng nhập 1 hoặc 2.")
        return

    choice = "option_1" if user_choice == '1' else "option_2"
    time_cost = int(current_scenario[2]) if user_choice == '1' else int(current_scenario[4])
    context.user_data['time'] += time_cost

    await update.message.reply_text(
        f"✅ Bạn đã chọn: {current_scenario[1] if user_choice == '1' else current_scenario[3]}\n"
        f"⏱️ Thời gian cộng thêm: {time_cost} giây."
    )
    await play(update, context)

# Handle question
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = fetch_csv_data(QUESTIONS_URL)
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
        "question": question[0],
        "options": question[1:4],
        "correct": question[4]
    }
    context.user_data['question_round'] += 1

    await update.message.reply_text(
        f"🤔 *Câu {context.user_data['question_round']} - Câu hỏi:*\n\n"
        f"{question[0]}\n\n"
        f"1️⃣ {question[1]}\n"
        f"2️⃣ {question[2]}\n"
        f"3️⃣ {question[3]}\n\n"
        "⏩ Nhập 1, 2 hoặc 3 để trả lời.",
        parse_mode="Markdown"
    )

# Handle answer
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip()
    current_question = context.user_data.get('current_question')

    if not current_question or user_choice not in ['1', '2', '3']:
        await update.message.reply_text("❌ Vui lòng nhập 1, 2 hoặc 3.")
        return

    correct_answer = current_question['correct']
    if user_choice == correct_answer:
        context.user_data['score'] += 10
        await update.message.reply_text(
            f"✅ Đúng rồi! Bạn đã trả lời đúng câu hỏi.\n"
            f"🎯 Điểm hiện tại: {context.user_data['score']} điểm."
        )
    else:
        await update.message.reply_text(
            f"❌ Sai rồi! Đáp án đúng là: {correct_answer}.\n"
            f"🎯 Điểm hiện tại: {context.user_data['score']} điểm."
        )
    await play(update, context)

# Summarize game
async def summarize_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🎉 **Kết thúc trò chơi!** 🎉\n\n"
        f"⏱️ Tổng thời gian: {context.user_data['time']} giây\n"
        f"🎯 Điểm số: {context.user_data['score']}\n"
        "✨ Cảm ơn bạn đã tham gia!",
        parse_mode="Markdown"
    )

# Main function
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
