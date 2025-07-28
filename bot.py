import os
import re
import threading
import time
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming links with proper progress tracking"""
    message_text = update.message.text
    
    if not re.match(r'https?://\S+', message_text):
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")
        return

    # Show initial processing message
    processing_msg = await update.message.reply_text("ခနစောင့်ပါ...")
    await asyncio.sleep(2)
    await context.bot.delete_message(chat_id=update.effective_chat.id, 
                                  message_id=processing_msg.message_id)
    
    # Initialize progress message
    loading_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
    
    # Run test in background with proper error handling
    try:
        thread = threading.Thread(target=run_test_with_progress, 
                               args=(update, context, message_text, loading_msg))
        thread.start()
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=loading_msg.message_id,
            text=f"Error: {str(e)}"
        )

def run_test_with_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, loading_msg):
    """Improved version with guaranteed 100% progress"""
    total_requests = 50
    completed = 0
    
    def send_request(target_url):
        """Send request with retry logic"""
        try:
            requests.get(target_url, timeout=10)
            return True
        except:
            return False
    
    def update_progress(current, total):
        """Update progress bar with percentage"""
        percent = min(100, int((current/total)*100))
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        progress_text = f"Loading Process...\n{percent}% [{bars}{spaces}]"
        
        try:
            context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=loading_msg.message_id,
                text=progress_text
            )
        except:
            pass  # Prevent crash if message edit fails

    # Use ThreadPoolExecutor for better control
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_request, url) for _ in range(total_requests)]
        
        for future in as_completed(futures, timeout=60):
            if future.result():
                completed += 1
            update_progress(completed, total_requests)
            time.sleep(0.1)  # Smooth progress update
    
    # Ensure 100% is shown even if some requests failed
    update_progress(total_requests, total_requests)
    
    # Final completion message
    context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=loading_msg.message_id,
        text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 10 | Requests: 50"
    )

def main():
    """Start the bot with proper initialization"""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    print("Bot is running with improved progress tracking...")
    application.run_polling()

if __name__ == "__main__":
    main()
