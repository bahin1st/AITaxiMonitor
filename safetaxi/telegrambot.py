from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7880331751:AAFjx7puCAbce9Eq4KfkWkEiw-B8OpBv5Z8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    print(f"Received /start from chat_id: {chat_id}")  # Log the chat_id
    
    
    
    await update.message.reply_text(
        f"💬Please write the Telegram chat id in your platform so can be updated regarding your rides. Your will receive alerts by telegram message. Your Telegram Chat ID is:\n",
        parse_mode='Markdown'
    )
    await update.message.reply_text(
        chat_id,
        parse_mode='Markdown'
    )


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    print("🚀 Bot is running...")  # Log that the bot is running
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    run_bot()
