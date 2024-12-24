import logging
import requests
import pandas as pd
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import random

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token and data URLs
TELEGRAM_BOT_TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
SCENARIO_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"
QUESTIONS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=1301413371"

# Initialize game state variables
game_state = {}

async def fetch_data(url):
    """Fetch data from a Google Sheets URL."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = pd.read_csv(io.StringIO(response.text))
        return data
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    chat_id = update.effective_chat.id
    game_state[chat_id] = {
        'score': 0,
        'time': 0,
        'prestige_stars': 0,
        'round': 1,
        'used_scenarios': [],
        'used_questions': []
    }
    welcome_message = (
        "Xin chào! Đây là bot GameFi của bạn.\n\n"
        "Hãy bắt đầu bằng cách sử dụng lệnh /play để chơi."
    )
    await update.message.reply_text(welcome_message)

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /play command to start or continue the game."""
    chat_id = update.effective_chat.id
    state = game_state.get(chat_id)

    if not state:
        await update.message.reply_text("Vui lòng sử dụng lệnh /start trước khi chơi.")
        return

    if state['round'] > 10:
        await summarize_game(update, context)
        return

    scenario_data = await fetch_data(SCENARIO_URL)
    if scenario_data is None:
        await update.message.reply_text("Không thể tải dữ liệu kịch bản. Vui lòng thử lại sau.")
        return

    unused_scenarios = scenario_data[~scenario_data['Scenario'].isin(state['used_scenarios'])]
    if unused_scenarios.empty:
        await update.message.reply_text("Hết kịch bản để chơi.")
        return

    scenario = unused_scenarios.sample(1).iloc[0]
    state['used_scenarios'].append(scenario['Scenario'])
    state['time'] += scenario['Time']
    state['prestige_stars'] += scenario['Prestige Stars']

    options = [
        InlineKeyboardButton(option, callback_data=f"scenario_{i}")
        for i, option in enumerate([scenario['Option 1'], scenario['Option 2'], scenario['Option 3']])
    ]

    reply_markup = InlineKeyboardMarkup.from_column(options)
    await update.message.reply_text(scenario['Scenario'], reply_markup=reply_markup)

async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's choice for a scenario."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    state = game_state.get(chat_id)

    if not state:
        await query.edit_message_text("Vui lòng sử dụng lệnh /start trước khi chơi.")
        return

    # Proceed to the question phase
    await ask_question(query, state)

async def ask_question(query, state):
    """Ask a random question that hasn't been used yet."""
    question_data = await fetch_data(QUESTIONS_URL)
    if question_data is None:
        await query.edit_message_text("Không thể tải dữ liệu câu hỏi. Vui lòng thử lại sau.")
        return

    unused_questions = question_data[~question_data['Question'].isin(state['used_questions'])]
    if unused_questions.empty:
        await query.edit_message_text("Hết câu hỏi để chơi.")
        return

    question = unused_questions.sample(1).iloc[0]
    state['used_questions'].append(question['Question'])

    options = [
        InlineKeyboardButton(option, callback_data=f"question_{i}")
        for i, option in enumerate([question['Option 1'], question['Option 2'], question['Option 3']])
    ]

    reply_markup = InlineKeyboardMarkup.from_column(options)
    await query.edit_message_text(question['Question'], reply_markup=reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's answer to a question."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    state = game_state.get(chat_id)

    if not state:
        await query.edit_message_text("Vui lòng sử dụng lệnh /start trước khi chơi.")
        return

    answer_correct = query.data.endswith("_0")  # Assume option_0 is correct
    if answer_correct:
        state['score'] += 10
        await query.edit_message_text("Chính xác! Bạn được cộng 10 điểm.")
    else:
        await query.edit_message_text("Sai rồi! Hãy thử câu hỏi tiếp theo.")

    state['round'] += 1

    if state['round'] > 10:
        await summarize_game(update, context)
    else:
        await play(update, context)

async def summarize_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summarize the game and send the results to the user."""
    chat_id = update.effective_chat.id
    state = game_state.get(chat_id)

    if not state:
        await update.message.reply_text("Vui lòng sử dụng lệnh /start trước khi chơi.")
        return

    summary = (
        f"Trò chơi đã kết thúc!\n\n"
        f"Điểm số: {state['score']}\n"
        f"Tổng thời gian: {state['time']} phút\n"
        f"Ngôi sao danh giá: {state['prestige_stars']}\n"
    )
    await update.message.reply_text(summary)
    del game_state[chat_id]

async def main():
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CallbackQueryHandler(handle_choice, pattern="^scenario_"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^question_"))

    # Start the bot
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
