# backend/simple_bot.py
import os
import logging
import json
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = flask.Flask(__name__)

@app.route('/')
def health_check():
    return 'Bot is running!'

@app.route('/health')
def health():
    return {'status': 'healthy'}

# Простая база данных в памяти (для демо)
users_db = {}
carts_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Сохраняем пользователя
    users_db[user.id] = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Открыть магазин", web_app={'url': os.getenv('WEBAPP_URL', 'https://yourusername.github.io/parfum-depo')})],
        [InlineKeyboardButton("💬 Чат с менеджером", url='https://t.me/parfumdepo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Добро пожаловать в ParfumDEPO, {user.first_name}! 🎉\n\n"
        "Здесь вы найдете эксклюзивные парфюмерные композиции со всего мира.",
        reply_markup=reply_markup
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из веб-приложения"""
    try:
        data = json.loads(update.message.web_app_data.data)
        user_id = update.effective_user.id
        action = data.get('action')
        
        if action == 'add_to_cart':
            product_id = data.get('product_id')
            if user_id not in carts_db:
                carts_db[user_id] = []
            carts_db[user_id].append(product_id)
            
            await update.message.reply_text("✅ Товар добавлен в корзину!")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке данных")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Основная функция запуска бота"""
    
    if not os.getenv('TELEGRAM_BOT_TOKEN'):
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return
    
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    application.add_error_handler(error_handler)
    
    port = int(os.environ.get('PORT', 8080))
    webhook_url = os.getenv('RAILWAY_STATIC_URL')
    
    if webhook_url:
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=os.getenv('TELEGRAM_BOT_TOKEN'),
            webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_BOT_TOKEN')}"
        )
    else:
        application.run_polling()

if __name__ == '__main__':
    main()
