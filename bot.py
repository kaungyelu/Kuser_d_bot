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
        await start_test_sequence(update, context)
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

async def start_test_sequence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the test sequence with countdown and progress"""
    # Send initial messages
    countdown_msg = await update.message.reply_text("ခနစောင့်ပါ...\n1:00")
    progress_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
    
    # Store message IDs for later editing
    context.user_data['countdown_msg_id'] = countdown_msg.message_id
    context.user_data['progress_msg_id'] = progress_msg.message_id
    
    # Start test in background
    thread = threading.Thread(target=run_test_with_countdown, 
                           args=(update, context))
    thread.start()

def run_test_with_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the test with countdown timer and progress bar"""
    url = context.user_data['url']
    countdown_msg_id = context.user_data['countdown_msg_id']
    progress_msg_id = context.user_data['progress_msg_id']
    
    total_requests = 50
    threads_count = 20
    completed_requests = 0
    start_time = time.time()
    duration = 10  # 10 seconds test duration
    
    def send_request():
        try:
            requests.get(url, timeout=5)
            return 1
        except:
            return 0
    
    def update_countdown(remaining):
        minutes = remaining // 60
        seconds = remaining % 60
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=countdown_msg_id,
            text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
        )
    
    def update_progress(completed):
        percent = min(100, int((completed/total_requests)*100))
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=progress_msg_id,
            text=progress_text
        )
        return percent
    
    # Run test for 10 seconds
    while time.time() - start_time < duration:
        # Update countdown
        remaining_time = int(duration - (time.time() - start_time))
        update_countdown(remaining_time)
        
        # Send requests
        threads = []
        successful_requests = 0
        
        for _ in range(threads_count):
            t = threading.Thread(target=lambda: [send_request() for _ in range(5)])
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        completed_requests += threads_count * 5
        current_percent = update_progress(completed_requests)
        
        # Sleep briefly to prevent too many updates
        time.sleep(0.5)
    
    # Final updates after test completes
    update_countdown(0)
    update_progress(total_requests)
    
    # Show completion message with "Again" button
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=progress_msg_id,
        text=f"လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: {threads_count} | Requests: {completed_requests}",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "test_again":
        # Delete old progress message
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except:
            pass
        
        # Restart the test
        await start_test_sequence(update, context)

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
