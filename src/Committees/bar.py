from . import base
import utils
import bx_utils

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext
)

class Bar(base.Committee_hub_base):
    def __init__(self):
        base.Activity.MENU = 10
        super().__init__(
            name=".9 Bar",
            extra_states={base.Activity.MENU: [MessageHandler(filters.PHOTO, self.menu_confirmation)]},
            extra_hub_handlers=[CommandHandler("menu", self.menu)]
        )
        self.info = bx_utils.db.get_committee_info(self.name)
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Asks for the receival of the menu"""
        if "menu_id" in self.info.keys():
            photo_id = self.info["menu_id"]
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="This was the previous menu")
            await context.bot.send_photo(chat_id=update.effective_chat.id,
                                         photo=photo_id)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Send the photo of the new menu")
        return self.state.MENU

    async def menu_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirms that the menu wants to be updated"""
        photo = update.message.photo[-1]
        photo_id = photo.file_id
        photo_obj = await context.bot.getFile(photo_id)
        await photo_obj.download_to_drive(custom_path=utils.config.ROOT + '/data/temp_files/menu.jpg')
        bx_utils.drive
        bx_utils.db.extra_committee_info(self.name, "menu_id", photo_id)
        self.info = bx_utils.db.get_committee_info(self.name)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Photo received")
        return self.state.HUB