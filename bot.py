import os
import re
import threading
import time
import requests
import asyncio
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: CallbackContext):
    """/start command ကိုတုံ့ပြန်ခြင်း"""
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: CallbackContext):
    """လင့်ခ်တစ်ခုရရှိပါက တုံ့ပြန်ခြင်း"""
    message_text = update.message.text
    
    if re.match(r'https?://\S+', message_text):
        # "ခနစောင့်ပါ..." မက်ဆေ့ဂျ်ကို 3စက္ကန့်ပြပြီးဖျက်မည်
        processing_msg = await update.message.reply_text("ခနစောင့်ပါ...")
        await asyncio.sleep(3)
        await context.bot.delete_message(chat_id=update.effective_chat.id, 
                                      message_id=processing_msg.message_id)
        
        # Loading progress bar စတင်မည်
        loading_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
        
        # Test ကို background thread တွင် စတင်မည်
        thread = threading.Thread(target=run_test, 
                               args=(update, context, message_text, loading_msg))
        thread.start()
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

def run_test(update: Update, context: CallbackContext, url: str, loading_msg):
    """URL ကို test လုပ်ခြင်း function"""
    total_requests = 50
    threads_count = 20
    completed = 0
    
    def send_request(url):
        """URL သို့ request ပို့ခြင်း"""
        try:
            requests.get(url, timeout=5)
        except:
            pass
    
    def update_progress(percent):
        """Progress bar ကို update လုပ်ခြင်း"""
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                    message_id=loading_msg.message_id,
                                    text=progress_text)
    
    # 5 batch (တစ်ခါကို 10 request စီ)
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
    
    # ပြီးဆုံးကြောင်း message ပြမည်
    context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                message_id=loading_msg.message_id,
                                text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50")

def main():
    """Bot ကို start လုပ်ခြင်း"""
    # use_context=True ကို ဖယ်ရှားထားပါ
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    # Command handlers
    dp.add_handler(CommandHandler("start", start_command))
    dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    # Polling method ကိုသုံးမည်
    print("Bot is starting...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
