import logging
import requests
import csv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Set up logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets URL (CSV Format)
DECISION_POINTS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"
QUESTIONS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"
PLAYER_STATS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"

# Read data from Google Sheets (CSV)
def fetch_csv_data(url):
    response = requests.get(url)
    decoded_content = response.content.decode("utf-8")
    return list(csv.reader(decoded_content.splitlines(), delimiter=","))

def start(update: Update, context: CallbackContext):
    """Handle the /start command."""
    user = update.effective_user
    context.user_data['current_point'] = 0  # Reset current decision point
    context.user_data['score'] = 0  # Reset score
    context.user_data['time'] = 0  # Reset time
    context.user_data['prestige_stars'] = 0  # Reset prestige stars

    welcome_message = (
        "🎮 **Chào mừng bạn đến với GameFi Nhập Vai!** 🎉\n\n"
        "Bạn sẽ bước vào một hành trình phiêu lưu đầy thách thức, nơi các quyết định của bạn sẽ ảnh hưởng đến điểm số, thời gian, và danh dự của bạn. 🌟\n\n"
        "⚔️ **Luật chơi:**\n"
        "1️⃣ Đi qua 10 điểm quyết định trên hành trình.\n"
        "2️⃣ Trả lời câu hỏi thử thách tài chính/trí tuệ.\n"
        "3️⃣ Mỗi quyết định sẽ ảnh hưởng đến thời gian của bạn (⏱️) và có thể mang lại Ngôi sao danh giá (🌟).\n\n"
        "🔥 **Mục tiêu:** Hoàn thành thử thách với điểm cao nhất và thời gian nhanh nhất.\n\n"
        "⏩ Gõ /play để bắt đầu hành trình của bạn!"
    )
    update.message.reply_text(welcome_message, parse_mode="Markdown")

def play(update: Update, context: CallbackContext):
    """Start the game by showing the first decision point."""
    decision_points = fetch_csv_data(DECISION_POINTS_URL)[1:]  # Skip header
    current_point = context.user_data.get('current_point', 0)

    if current_point >= len(decision_points):
        summarize_game(update, context)
        return

    point = decision_points[current_point]
    scenario = point[0]
    option_1 = point[1]
    time_1 = point[2]
    option_2 = point[3]
    time_2 = point[4]

    context.user_data['current_scenario'] = point  # Save current scenario for processing

    message = (
        f"🗺️ *{scenario}*\n\n"
        f"1️⃣ {option_1} (+{time_1} giây)\n"
        f"2️⃣ {option_2} (+{time_2} giây)\n\n"
        f"⏩ Nhập số 1 hoặc 2 để chọn lựa của bạn."
    )
    update.message.reply_text(message, parse_mode="Markdown")

def handle_choice(update: Update, context: CallbackContext):
    """Handle the player's choice at a decision point."""
    user_choice = update.message.text
    current_scenario = context.user_data.get('current_scenario', None)

    if not current_scenario or user_choice not in ['1', '2']:
        update.message.reply_text("❌ Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")
        return

    choice_index = 1 if user_choice == '1' else 3
    time_cost = int(current_scenario[choice_index + 1])
    prestige_star = current_scenario[5] == f"Option {user_choice}"

    context.user_data['time'] += time_cost
    if prestige_star:
        context.user_data['prestige_stars'] += 1

    update.message.reply_text(
        f"✅ Bạn đã chọn: {current_scenario[choice_index]}\n"
        f"⏱️ Thời gian thêm: {time_cost} giây.\n"
        f"🌟{' Bạn nhận được một Ngôi sao danh giá!' if prestige_star else ''}"
    )

    context.user_data['current_point'] += 1
    play(update, context)

def summarize_game(update: Update, context: CallbackContext):
    """Summarize the game results."""
    score = context.user_data.get('score', 0)
    time = context.user_data.get('time', 0)
    prestige_stars = context.user_data.get('prestige_stars', 0)

    summary = (
        f"🎉 **Hành trình của bạn đã kết thúc!** 🎉\n\n"
        f"⏳ *Tổng thời gian:* **{time} giây**\n"
        f"🏆 *Tổng điểm:* **{score} điểm**\n"
        f"🌟 *Ngôi sao danh giá:* **{prestige_stars}**\n\n"
        f"✨ **Cảm ơn bạn đã tham gia GameFi Nhập Vai!** ✨"
    )
    update.message.reply_text(summary, parse_mode="Markdown")

def main():
    """Main function to run the bot."""
    TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("play", play))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_choice))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
