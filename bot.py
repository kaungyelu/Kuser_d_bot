import os
import re
import threading
import time
import requests
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TestSession:
    def __init__(self):
        self.active = False
        self.countdown_value = 60
        self.progress = 0

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    chat_id = update.effective_chat.id
    
    if re.match(r'https?://\S+', message_text):
        # Initialize new test session
        context.user_data['session'] = TestSession()
        context.user_data['session'].active = True
        context.user_data['url'] = message_text
        
        # Send countdown message
        countdown_msg = await update.message.reply_text("ခနစောင့်ပါ...\n1:00")
        context.user_data['countdown_msg_id'] = countdown_msg.message_id
        
        # Start countdown in background
        asyncio.create_task(run_countdown(update, context, chat_id))
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

async def run_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    session = context.user_data.get('session')
    if not session:
        return
    
    countdown_msg_id = context.user_data['countdown_msg_id']
    
    for i in range(60, -1, -1):
        if not session.active:
            break
            
        session.countdown_value = i
        minutes = i // 60
        seconds = i % 60
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=countdown_msg_id,
                text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
            )
        except Exception as e:
            print(f"Error editing message: {e}")
            break
        
        await asyncio.sleep(1)
    
    # Countdown finished, start progress
    if session.active:
        await start_progress(update, context, chat_id)

async def start_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    session = context.user_data.get('session')
    if not session or not session.active:
        return
    
    # Delete countdown message
    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=context.user_data['countdown_msg_id']
        )
    except:
        pass
    
    # Send progress message
    progress_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Loading Process...\n0% [░░░░░░░░░░]"
    )
    context.user_data['progress_msg_id'] = progress_msg.message_id
    
    # Run progress update
    await update_progress(update, context, chat_id)

async def update_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    session = context.user_data.get('session')
    if not session or not session.active:
        return
    
    progress_msg_id = context.user_data['progress_msg_id']
    url = context.user_data['url']
    duration = 60  # 1 minute
    start_time = time.time()
    
    def send_request():
        try:
            requests.get(url, timeout=5)
        except:
            pass
    
    while time.time() - start_time < duration:
        if not session.active:
            break
            
        elapsed = time.time() - start_time
        percent = min(100, int((elapsed/duration)*100))
        session.progress = percent
        
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=progress_msg_id,
                text=f"Loading Process...\n{percent}% [{bars}{spaces}]"
            )
            
            # Send requests in background
            threading.Thread(target=send_request).start()
            
        except Exception as e:
            print(f"Error updating progress: {e}")
            break
        
        await asyncio.sleep(1)
    
    # Test completed
    if session.active:
        await show_results(update, context, chat_id)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    session = context.user_data.get('session')
    if not session:
        return
    
    # Delete progress message after delay
    await asyncio.sleep(10)
    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=context.user_data['progress_msg_id']
        )
    except:
        pass
    
    # Send results with Again button
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50",
        reply_markup=reply_markup
    )
    
    # Clean up session
    session.active = False

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        # Restart the process
        if 'url' in context.user_data:
            await handle_link(update, context)

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
