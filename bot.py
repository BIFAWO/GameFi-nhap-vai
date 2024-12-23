import logging
import requests
import csv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT, COMMAND

# Set up logging
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets URL (CSV Format)
DECISION_POINTS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"

# Read data from Google Sheets (CSV)
def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        decoded_content = response.content.decode("utf-8")
        return list(csv.reader(decoded_content.splitlines(), delimiter=","))
    except Exception as e:
        logger.error("Error fetching CSV data: %s", e)
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Handling /start from user: %s", update.effective_user.username)
    context.user_data['current_point'] = 0
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

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("User %s started playing", update.effective_user.username)
    decision_points = fetch_csv_data(DECISION_POINTS_URL)
    if not decision_points:
        if update.message:
            await update.message.reply_text("❌ Không thể tải dữ liệu trò chơi. Vui lòng thử lại sau.")
        return

    current_point = context.user_data.get('current_point', 0)
    if current_point >= len(decision_points):
        await summarize_game(update, context)
        return

    point = decision_points[current_point]
    message = (
        f"🗺️ *{point[0]}*\n\n"
        f"1️⃣ {point[1]} (+{point[2]} giây)\n"
        f"2️⃣ {point[3]} (+{point[4]} giây)\n\n"
        f"⏩ Nhập số 1 hoặc 2 để chọn."
    )
    if update.message:
        await update.message.reply_text(message, parse_mode="Markdown")

async def summarize_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    if update.message:
        await update.message.reply_text(summary, parse_mode="Markdown")

async def log_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Update received: %s", update)

def main():
    TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
    application = Application.builder().token(TOKEN).build()

    logger.info("Bot is starting with token: %s", TOKEN)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(MessageHandler(TEXT | COMMAND, log_updates))

    application.run_polling()

if __name__ == "__main__":
    logger.info("Bot is initializing...")
    main()
