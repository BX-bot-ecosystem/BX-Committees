import googleapiclient.errors

from . import base
import utils
import bx_utils
import os

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
        base.Activity.DRINKS = 11
        base.Activity.ADD_DRINK = 12
        base.Activity.DELETE_DRINK = 13
        base.Activity.SNACKS = 14
        base.Activity.ADD_SNACK = 12
        base.Activity.DELETE_SNACK = 13
        super().__init__(
            name=".9 Bar",
            extra_states={base.Activity.MENU: [MessageHandler(filters.PHOTO, self.menu_confirmation)],
                          base.Activity.DRINKS: [CallbackQueryHandler(self.stock_update)],
                          base.Activity.ADD_DRINK: [MessageHandler(filters.TEXT, self.add_drink)],
                          base.Activity.DELETE_DRINK: [CallbackQueryHandler(self.delete_drink)],
                          base.Activity.SNACKS: [CallbackQueryHandler(self.snack_update)],
                          base.Activity.ADD_SNACK: [MessageHandler(filters.TEXT, self.add_snack)],
                          base.Activity.DELETE_SNACK: [CallbackQueryHandler(self.delete_snack)]
                          },
            extra_hub_handlers=[CommandHandler("menu", self.menu),
                                CommandHandler("stock", self.stocked_drinks),
                                CommandHandler("snack", self.snack_update)]
        )
        self.info = bx_utils.db.get_committee_info(self.name)
    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Asks for the receival of the menu"""
        file_path = utils.config.ROOT +  '/data/menu.jpg'
        try:
            bx_utils.drive.download_committee_file(self.name, 'menu.jpg', file_path)
            with open(file_path, 'rb') as file:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text="This was the old menu")
                await context.bot.send_photo(chat_id=update.effective_chat.id,
                                             photo=file)
        except googleapiclient.errors.HttpError:
            pass
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Send the photo of the new menu")
        return self.state.MENU

    async def menu_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Confirms that the menu wants to be updated"""
        photo = update.message.photo[-1]
        photo_id = photo.file_id
        photo_obj = await context.bot.getFile(photo_id)
        await photo_obj.download_to_drive(custom_path=utils.config.ROOT + '/data/menu.jpg')
        bx_utils.drive.upload_image_to_committee(self.name, utils.config.ROOT + '/data/menu.jpg')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Photo received")
        return self.state.HUB

    async def stocked_drinks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allows to modify the accesible drinks through the order functionality"""
        try:
            self.current_drinks = bx_utils.db.get_committee_info(self.name)["drinks"]
        except KeyError:
            self.current_drinks = ''
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The current drinks are: {self.current_drinks} \nWhat do you want to do?",
                                       reply_markup=self.create_keyboard(["Add", "Delete"]))
        return self.state.DRINKS

    async def stock_update(self, update: Update, context: CallbackContext):
        self.drinks = bx_utils.db.db_to_list(self.current_drinks)
        query = update.callback_query
        await query.answer()
        answer = query.data
        if answer == 'Nay':
            await query.edit_message_text(text='Alright')
            return self.state.HUB
        if answer == 'Add':
            await query.edit_message_text(text='Send the name of the new drink')
            return self.state.ADD_DRINK
        if answer == 'Delete':
            await query.edit_message_text(text="Which drink do you want to delete", reply_markup=self.create_keyboard(self.drinks))
            return self.state.DELETE_DRINK

    async def add_drink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        drink = update.message.text
        self.drinks.append(drink)
        drink_string = bx_utils.db.list_to_db(self.drinks)
        bx_utils.db.extra_committee_info(self.name, "drinks", drink_string)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="List updated")
        return self.state.HUB

    async def delete_drink(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'Nay':
            await query.edit_message_text(text='Alright')
            return self.state.HUB
        drink = query.data
        self.drinks.remove(drink)
        drink_string = bx_utils.db.list_to_db(self.drinks)
        bx_utils.db.extra_committee_info(self.name, "drinks", drink_string)
        await query.edit_message_text(text='List updated')
        return self.state.HUB


    async def stocked_snacks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Allows to modify the accesible drinks through the order functionality"""
        try:
            self.current_snacks = bx_utils.db.get_committee_info(self.name)["snacks"]
        except KeyError:
            self.current_snacks = ''
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The current snacks are: {self.current_snacks} \nWhat do you want to do?",
                                       reply_markup=self.create_keyboard(["Add", "Delete"]))
        return self.state.SNACKS

    async def snack_update(self, update: Update, context: CallbackContext):
        self.snacks = bx_utils.db.db_to_list(self.current_snacks)
        query = update.callback_query
        await query.answer()
        answer = query.data
        if answer == 'Nay':
            await query.edit_message_text(text='Alright')
            return self.state.HUB
        if answer == 'Add':
            await query.edit_message_text(text='Send the name of the new snack')
            return self.state.ADD_SNACK
        if answer == 'Delete':
            await query.edit_message_text(text="Which snack do you want to delete", reply_markup=self.create_keyboard(self.snacks))
            return self.state.DELETE_SNACK

    async def add_snack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        snack = update.message.text
        self.snacks.append(snack)
        snack_string = bx_utils.db.list_to_db(self.snacks)
        bx_utils.db.extra_committee_info(self.name, "snacks", snack_string)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="List updated")
        return self.state.HUB

    async def delete_snack(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'Nay':
            await query.edit_message_text(text='Alright')
            return self.state.HUB
        snack = query.data
        self.snacks.remove(snack)
        snack_string = bx_utils.db.list_to_db(self.snacks)
        bx_utils.db.extra_committee_info(self.name, "snacks", snack_string)
        await query.edit_message_text(text='List updated')
        return self.state.HUB
