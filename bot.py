import logging
import requests
import csv
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes
from telegram.ext.filters import TEXT, COMMAND

# Logging setup
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets URL cho danh sách Scenario
DECISION_POINTS_URL = "https://docs.google.com/spreadsheets/d/1sOqCrOl-kTKKQQ0ioYzYkqJwRM9qxsndxiLmo_RDZjI/export?format=csv&gid=0"

# Hàm tải dữ liệu từ Google Sheets
def fetch_csv_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        decoded_content = response.content.decode("utf-8")
        data = list(csv.reader(decoded_content.splitlines(), delimiter=","))
        return data[1:]  # Bỏ dòng tiêu đề
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        return []

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['used_scenarios'] = set()
    context.user_data['scenario_count'] = 0

    await update.message.reply_text(
        "🎮 **Chào mừng bạn đến với GameFi Nhập Vai!** 🎉\n\n"
        "⏩ Gõ /play để bắt đầu chơi!",
        parse_mode="Markdown"
    )

# /play command
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data['scenario_count'] >= 10:
        await update.message.reply_text(
            "🏁 Bạn đã hoàn thành tất cả 10 kịch bản!\n"
            "Cảm ơn bạn đã chơi.",
            parse_mode="Markdown"
        )
        return

    # Lấy danh sách Scenario
    scenarios = fetch_csv_data(DECISION_POINTS_URL)
    if not scenarios:
        await update.message.reply_text("❌ Không thể tải danh sách kịch bản. Vui lòng thử lại sau.")
        return

    # Lọc ra các kịch bản chưa được sử dụng
    unused_scenarios = [s for s in scenarios if s[0] not in context.user_data['used_scenarios']]
    if not unused_scenarios:
        await update.message.reply_text("⚠️ Không còn kịch bản nào mới để chơi.")
        return

    # Chọn một Scenario ngẫu nhiên
    scenario = random.choice(unused_scenarios)
    context.user_data['used_scenarios'].add(scenario[0])
    context.user_data['current_scenario'] = scenario
    context.user_data['scenario_count'] += 1

    # Gửi kịch bản cho người chơi
    await update.message.reply_text(
        f"🗺️ *Kịch bản {context.user_data['scenario_count']}*\n\n"
        f"{scenario[0]}\n\n"
        f"1️⃣ {scenario[1]}\n"
        f"2️⃣ {scenario[3]}\n\n"
        "⏩ Nhập 1 hoặc 2 để chọn.",
        parse_mode="Markdown"
    )

# Xử lý lựa chọn của người chơi
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_choice = update.message.text.strip()
    current_scenario = context.user_data.get('current_scenario')

    # Kiểm tra xem người chơi đã chọn kịch bản hay chưa
    if not current_scenario:
        await update.message.reply_text("❌ Không có kịch bản nào đang chạy. Gõ /play để bắt đầu.")
        return

    # Đảm bảo lựa chọn hợp lệ
    if user_choice not in ['1', '2']:
        await update.message.reply_text("❌ Vui lòng nhập 1 hoặc 2.")
        return

    # Xử lý phản hồi dựa trên lựa chọn
    chosen_option = current_scenario[1] if user_choice == '1' else current_scenario[3]
    await update.message.reply_text(
        f"✅ Bạn đã chọn: {chosen_option}.\n"
        f"⏩ Chuyển sang kịch bản tiếp theo..."
    )

    # Tiếp tục chơi
    await play(update, context)

# Main function
def main():
    TOKEN = "7595985963:AAGoUSk8pIpAiSDaQwTufWqmYs3Kvn5mmt4"
    application = Application.builder().token(TOKEN).build()

    # Thêm các lệnh xử lý
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(MessageHandler(TEXT & ~COMMAND, handle_choice))

    # Chạy bot
    application.run_polling()

if __name__ == "__main__":
    main()
