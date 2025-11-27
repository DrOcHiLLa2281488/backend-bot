# backend/bot.py
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from supabase import create_client, Client

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Supabase
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Сохраняем пользователя в базу
    supabase.table('users').upsert({
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name
    }).execute()
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Открыть магазин", web_app={'url': os.getenv('WEBAPP_URL')})],
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
    data = json.loads(update.message.web_app_data.data)
    user_id = update.effective_user.id
    action = data.get('action')
    
    if action == 'add_to_cart':
        product_id = data.get('product_id')
        # Добавляем товар в корзину
        supabase.table('carts').upsert({
            'user_id': user_id,
            'product_id': product_id,
            'quantity': data.get('quantity', 1)
        }).execute()
        
        await update.message.reply_text("✅ Товар добавлен в корзину!")

if __name__ == '__main__':
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    port = int(os.environ.get('PORT', 8443))
    webhook_url = os.getenv('RAILWAY_STATIC_URL') or f"https://{os.getenv('RAILWAY_SERVICE_NAME')}.up.railway.app"
    
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=os.getenv('TELEGRAM_BOT_TOKEN'),
        webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_BOT_TOKEN')}"
    )
