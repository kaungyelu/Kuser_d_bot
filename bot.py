import os
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ကျေးဇူးပြု၍ လင့်ခ်တစ်ခုပေးပို့ပါ")

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    chat_id = update.effective_chat.id
    
    if re.match(r'https?://\S+', message_text):
        context.user_data['url'] = message_text
        context.user_data['active'] = True
        
        # Send countdown message
        countdown_msg = await update.message.reply_text("ခနစောင့်ပါ...\n1:00")
        context.user_data['countdown_msg_id'] = countdown_msg.message_id
        
        # Start countdown and test
        asyncio.create_task(run_countdown(update, context, chat_id))
        asyncio.create_task(run_test(update, context, chat_id))
    else:
        await update.message.reply_text("လင့်ခ်မှန်ကန်စွာပေးပို့ပါ")

async def run_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    for i in range(60, -1, -1):
        if not context.user_data.get('active', False):
            break
            
        minutes = i // 60
        seconds = i % 60
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=context.user_data['countdown_msg_id'],
                text=f"ခနစောင့်ပါ...\n{minutes}:{seconds:02d}"
            )
        except:
            break
        
        await asyncio.sleep(1)
    
    # Countdown finished
    if context.user_data.get('active', False):
        try:
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=context.user_data['countdown_msg_id']
            )
        except:
            pass

async def run_test(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    # Wait until countdown reaches 30 seconds
    await asyncio.sleep(30)
    
    if not context.user_data.get('active', False):
        return
    
    # Send progress message
    progress_msg = await update.message.reply_text("Loading Process...\n0% [░░░░░░░░░░]")
    context.user_data['progress_msg_id'] = progress_msg.message_id
    
    # Run progress for 1 minute
    start_time = time.time()
    while time.time() - start_time < 60:
        if not context.user_data.get('active', False):
            break
            
        elapsed = time.time() - start_time
        percent = min(100, int((elapsed/60)*100))
        
        bars = '█' * int(percent/10)
        spaces = '░' * (10 - int(percent/10))
        
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=context.user_data['progress_msg_id'],
                text=f"Loading Process...\n{percent}% [{bars}{spaces}]"
            )
        except:
            break
        
        await asyncio.sleep(1)
    
    # Test completed
    if context.user_data.get('active', False):
        await show_results(update, context, chat_id)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id):
    context.user_data['active'] = False
    
    # Delete progress message after 10 seconds
    await asyncio.sleep(10)
    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=context.user_data['progress_msg_id']
        )
    except:
        pass
    
    # Send results
    keyboard = [[InlineKeyboardButton("Again", callback_data="test_again")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="လုပ်ဆောင်မှုပြီးမြောက်ပါပြီ ✓\nThreads: 20 | Requests: 50",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "test_again":
        # Delete old message
        try:
            await context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )
        except:
            pass
        
        # Restart
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
    import time
    main()
