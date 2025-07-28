import os
import re
import threading
import time
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming links"""
    message_text = update.message.text
    
    if re.match(r'https?://\S+', message_text):
        context.user_data['url'] = message_text
        await start_countdown(update, context)
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

async def start_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the countdown from 1:00 to 0:00"""
    countdown_msg = await update.message.reply_text("ခနစောင့်ပါ...\n1:00")
    context.user_data['countdown_msg_id'] = countdown_msg.message_id
    
    # Run countdown in background
    thread = threading.Thread(target=run_countdown, args=(update, context))
    thread.start()

def run_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the countdown timer"""
    countdown_msg_id = context.user_data['countdown_msg_id']
    
    for i in range(60, -1, -1):
        minutes = i // 60
        seconds = i % 60
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=countdown_msg_id,
            text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
        )
        time.sleep(1)
    
    # Countdown finished, start progress bar
    start_progress_bar(update, context)

def start_progress_bar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the progress bar after countdown"""
    # Delete countdown message
    try:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=context.user_data['countdown_msg_id']
        )
    except:
        pass
    
    # Send progress bar
    progress_msg = context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Loading Process...\n0% [░░░░░░░░░░]"
    )
    context.user_data['progress_msg_id'] = progress_msg.message_id
    
    # Run test in background
    thread = threading.Thread(target=run_test, args=(update, context))
    thread.start()

def run_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the test with progress bar"""
    url = context.user_data['url']
    progress_msg_id = context.user_data['progress_msg_id']
    total_requests = 50
    threads_count = 20
    duration = 60  # 1 minute for progress bar
    start_time = time.time()
    
    def send_request():
        try:
            requests.get(url, timeout=5)
            return 1
        except:
            return 0
    
    def update_progress(percent):
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=progress_msg_id,
            text=progress_text
        )
    
    # Run test for 1 minute
    while time.time() - start_time < duration:
        elapsed = time.time() - start_time
        percent = min(100, int((elapsed/duration)*100))
        
        # Send some requests (not too many to avoid rate limiting)
        threads = []
        for _ in range(threads_count):
            t = threading.Thread(target=send_request)
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        update_progress(percent)
        time.sleep(1)
    
    # Test completed, show results
    show_results(update, context)

def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show test results with Again button"""
    progress_msg_id = context.user_data['progress_msg_id']
    
    # Delete progress message after 10 seconds
    time.sleep(10)
    try:
        context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=progress_msg_id
        )
    except:
        pass
    
    # Send results with Again button
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Again button callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "test_again":
        # Delete old result message
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except:
            pass
        
        # Restart the process
        await start_countdown(update, context)

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
