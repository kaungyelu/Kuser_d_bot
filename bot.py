import os
import re
import threading
import time
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get('PORT', 8443))

async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: CallbackContext):
    message_text = update.message.text
    
    if re.match(r'https?://\S+', message_text):
        processing_msg = await update.message.reply_text("ခနစောင့်ပါ...")
        await asyncio.sleep(3)
        await context.bot.delete_message(chat_id=update.effective_chat.id, 
                                      message_id=processing_msg.message_id)
        
        loading_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
        
        thread = threading.Thread(target=run_test, 
                               args=(update, context, message_text, loading_msg))
        thread.start()
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

def run_test(update: Update, context: CallbackContext, url: str, loading_msg):
    total_requests = 50
    threads_count = 20
    completed = 0
    
    def send_request(url):
        try:
            requests.get(url, timeout=5)
        except:
            pass
    
    def update_progress(percent):
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                    message_id=loading_msg.message_id,
                                    text=progress_text)
    
    for _ in range(5):
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
        time.sleep(1)
    
    context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                message_id=loading_msg.message_id,
                                text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    
    # Railway deployment settings
    updater.start_webhook(listen="0.0.0.0",
                         port=PORT,
                         url_path=TOKEN,
                         webhook_url=f"https://your-app-name.railway.app/{TOKEN}")
    
    updater.idle()

if __name__ == "__main__":
    main()
