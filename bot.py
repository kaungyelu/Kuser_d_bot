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
        context.user_data['url'] = message_text  # Store URL for later use
        await countdown_timer(update, context)
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

async def countdown_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show countdown from 1:00 to 0:00"""
    processing_msg = await update.message.reply_text("ခနစောင့်ပါ...")
    
    for i in range(60, -1, -1):
        minutes = i // 60
        seconds = i % 60
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=processing_msg.message_id,
            text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
        )
        await asyncio.sleep(1)
    
    await start_test(update, context, processing_msg)

async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE, processing_msg):
    """Start the test after countdown"""
    url = context.user_data['url']
    loading_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
    
    thread = threading.Thread(target=run_test, 
                           args=(update, context, url, loading_msg, processing_msg))
    thread.start()

def run_test(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg, processing_msg):
    """Run the URL test"""
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
        context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=loading_msg.message_id,
            text=progress_text
        )
    
    # Run test for 10 seconds
    start_time = time.time()
    while time.time() - start_time < 10:
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
    
    # Show completion message with "Again" button
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=loading_msg.message_id,
        text=f"လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50",
        reply_markup=reply_markup
    )
    
    # Delete the processing message
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=processing_msg.message_id
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "test_again":
        await countdown_timer(update, context)

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
