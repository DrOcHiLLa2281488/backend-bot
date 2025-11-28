# backend/bot.py
import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from supabase import create_client, Client
import flask

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app для health checks
app = flask.Flask(__name__)

@app.route('/')
def health_check():
    return 'Bot is running!'

@app.route('/health')
def health():
    return {'status': 'healthy'}

# Инициализация Supabase с обработкой ошибок
def init_supabase():
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("Supabase URL or KEY not set")
            return None
            
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        logger.error(f"Error initializing Supabase: {e}")
        return None

supabase = init_supabase()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Сохраняем пользователя в базу, если Supabase доступен
    if supabase:
        try:
            supabase.table('users').upsert({
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }).execute()
        except Exception as e:
            logger.error(f"Error saving user: {e}")
    
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
        
        if action == 'add_to_cart' and supabase:
            product_id = data.get('product_id')
            # Добавляем товар в корзину
            supabase.table('carts').upsert({
                'user_id': user_id,
                'product_id': product_id,
                'quantity': data.get('quantity', 1)
            }).execute()
            
            await update.message.reply_text("✅ Товар добавлен в корзину!")
    except Exception as e:
        logger.error(f"Error handling web app data: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке данных")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Основная функция запуска бота"""
    
    # Проверяем обязательные переменные
    required_vars = ['TELEGRAM_BOT_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return
    
    # Создаем Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Получаем порт из переменных окружения Railway
    port = int(os.environ.get('PORT', 8080))
    webhook_url = os.getenv('RAILWAY_STATIC_URL') or f"https://{os.getenv('RAILWAY_SERVICE_NAME')}.up.railway.app"
    
    logger.info(f"Starting bot on port {port}")
    logger.info(f"Webhook URL: {webhook_url}")
    logger.info(f"Supabase initialized: {supabase is not None}")
    
    # Запускаем бота
    if os.getenv('RAILWAY_ENVIRONMENT'):
        # В Railway используем webhook
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=os.getenv('TELEGRAM_BOT_TOKEN'),
            webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_BOT_TOKEN')}"
        )
    else:
        # Локально используем polling
        application.run_polling()

if __name__ == '__main__':
    main()
