import os
import re
import threading
import time
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TestManager:
    def __init__(self):
        self.active_tests = {}
        self.lock = threading.Lock()

    def add_test(self, chat_id, url):
        with self.lock:
            self.active_tests[chat_id] = {
                'url': url,
                'running': True,
                'progress': 0,
                'countdown': 60
            }

    def stop_test(self, chat_id):
        with self.lock:
            if chat_id in self.active_tests:
                self.active_tests[chat_id]['running'] = False
                return True
            return False

    def get_test(self, chat_id):
        with self.lock:
            return self.active_tests.get(chat_id)

    def remove_test(self, chat_id):
        with self.lock:
            if chat_id in self.active_tests:
                del self.active_tests[chat_id]

test_manager = TestManager()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming links"""
    message_text = update.message.text
    chat_id = update.effective_chat.id
    
    if re.match(r'https?://\S+', message_text):
        test_manager.add_test(chat_id, message_text)
        
        # Send countdown message
        countdown_msg = await update.message.reply_text("ခနစောင့်ပါ...\n1:00")
        context.user_data['countdown_msg_id'] = countdown_msg.message_id
        
        # Start countdown in background
        countdown_thread = threading.Thread(
            target=run_countdown, 
            args=(update, context, chat_id)
        )
        countdown_thread.start()
        
        # Start test in background
        test_thread = threading.Thread(
            target=run_test, 
            args=(update, context, chat_id)
        )
        test_thread.start()
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

def run_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    """Run countdown from 1:00 to 0:00"""
    countdown_msg_id = context.user_data['countdown_msg_id']
    
    for i in range(60, -1, -1):
        if not test_manager.get_test(chat_id) or not test_manager.get_test(chat_id)['running']:
            break
            
        minutes = i // 60
        seconds = i % 60
        try:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=countdown_msg_id,
                text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
            )
        except:
            break
        
        test_manager.get_test(chat_id)['countdown'] = i
        time.sleep(1)
    
    # Countdown finished, delete message
    try:
        context.bot.delete_message(
            chat_id=chat_id,
            message_id=countdown_msg_id
        )
    except:
        pass

def run_test(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    """Run the actual test with progress bar"""
    test_data = test_manager.get_test(chat_id)
    if not test_data:
        return
    
    url = test_data['url']
    total_duration = 60  # 1 minute for progress
    start_time = time.time()
    
    # Send initial progress message
    progress_msg = context.bot.send_message(
        chat_id=chat_id,
        text="Loading Process...\n0% [░░░░░░░░░░]"
    )
    progress_msg_id = progress_msg.message_id
    
    def send_request():
        try:
            requests.get(url, timeout=5)
            return True
        except:
            return False
    
    def update_progress(percent):
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        try:
            context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg_id,
                text=progress_text
            )
        except:
            pass
    
    # Wait until countdown reaches 0
    while test_manager.get_test(chat_id) and test_manager.get_test(chat_id)['countdown'] > 0:
        time.sleep(0.1)
    
    # Now start the progress bar
    while time.time() - start_time < total_duration:
        if not test_manager.get_test(chat_id) or not test_manager.get_test(chat_id)['running']:
            break
            
        elapsed = time.time() - start_time
        percent = min(100, int((elapsed/total_duration)*100))
        
        # Send requests in background
        threading.Thread(target=send_request).start()
        
        update_progress(percent)
        time.sleep(1)
    
    # Test completed
    test_manager.stop_test(chat_id)
    
    # Delete progress message after 10 seconds
    time.sleep(10)
    try:
        context.bot.delete_message(
            chat_id=chat_id,
            message_id=progress_msg_id
        )
    except:
        pass
    
    # Send results with Again button
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(
        chat_id=chat_id,
        text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Again button callback"""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    
    if query.data == "test_again":
        # Delete old result message
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=query.message.message_id
            )
        except:
            pass
        
        # Restart the process with stored URL
        test_data = test_manager.get_test(chat_id)
        if test_data:
            await handle_link(update, context)

def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
