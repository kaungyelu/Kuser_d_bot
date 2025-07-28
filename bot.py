from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os
import re
import threading
import requests
import time

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command"""
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for when user sends a link"""
    message_text = update.message.text
    
    if re.match(r'https?://\S+', message_text):
        processing_msg = await update.message.reply_text("ခနစောင့်ပါ...")
        await context.bot.delete_message(chat_id=update.effective_chat.id, 
                                        message_id=processing_msg.message_id)
        
        loading_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
        
        # Run the test in background
        thread = threading.Thread(target=run_test, 
                                args=(update, context, message_text, loading_msg))
        thread.start()
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

def run_test(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg):
    """Function to run the test and update progress"""
    total_requests = 50
    threads_count = 20
    completed = 0
    
    def send_request(url):
        try:
            requests.get(url)
        except Exception as e:
            pass
    
    def update_progress(percent):
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                    message_id=loading_msg.message_id,
                                    text=progress_text)
    
    for i in range(5):  # 5 batches of 10 requests (total 50)
        threads = []
        for _ in range(threads_count):
            t = threading.Thread(target=send_request, args=(url,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        completed += 10
        percent = min(100, int((completed/total_requests)*100))
        update_progress(percent)
        time.sleep(0.5)
    
    # Completion message
    context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                message_id=loading_msg.message_id,
                                text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50")

def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    print("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
