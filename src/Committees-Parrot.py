import json
import enum

from telegram_bot_calendar import WYearTelegramCalendar, LSTEP
import utils
import bx_utils

import Committees

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

from dotenv import load_dotenv
import os
load_dotenv()

COMMITTEES_TOKEN = os.getenv("SAILORE_COMMITTEE_BOT")
PARROT_TOKEN = os.getenv("SAILORE_PARROT_BOT")
SAILORE_TOKEN = os.getenv("SAILORE_BX_BOT")

with open(utils.config.ROOT + '/data/committees.json') as f:
    committees = json.load(f)

bx_utils.logger(__name__)

class Activity(enum.Enum):
    HOME = 0
    LOGIN = 1
    VERIFICATION = 2
    HUB = 4

class Committees_Login:
    def __init__(self):
        self.active_committee = ''
        self.state = Activity.HOME
        self.committee_hub = ''
        self.access_list = []
        self.login_handler=ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT, self.start)],
            states={
                self.state.HOME: [
                    MessageHandler(filters.TEXT, self.start)
                ],
                self.state.LOGIN: [
                    CommandHandler("password", self.password_access),
                    MessageHandler(filters.TEXT, self.login)
                ],
                self.state.VERIFICATION: [
                    MessageHandler(filters.TEXT, self.verify_password)
                ],
                self.state.HUB: [

                ]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.start)]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        bx_utils.db.add_to_db(update.effective_user)
        info = bx_utils.db.get_user_info(update.effective_user)
        rights = info["rights"]
        access_list = bx_utils.db.db_to_list(rights)
        message_list = bx_utils.db.list_to_telegram(access_list)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="This bot is for committees to manage their bot sections")
        if len(access_list) == 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you don't have access to any committees")
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="Right now you have access to the following committees \n" + message_list)
            self.access_list = access_list
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="To gain admin access to a new committee ask your committee head for a one time password")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Once generated use the command /password to gain access")
        return self.state.LOGIN
    async def login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        committee = update.message.text
        if committee in self.access_list:
            self.active_committee = [committee_name for committee_name in committees.keys() if committees[committee_name]["command"] == committee][0]
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"You have successfully logged in")
            self.update_hub()
            await self.committee_hub.hub(update, context)
            return self.state.HUB
        else:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text="That is not a valid choice, either you don't have access or it doesn't exist")
            return self.state.HOME

    def update_hub(self):
        """
        Gain access to the specific hub or the generic one with the given name adjusted
        """
        if self.active_committee in Committees.committees.keys():
            self.committee_hub = Committees.committees[self.active_committee]
        else:
            self.committee_hub = Committees.Committee_hub_base(self.active_committee)
        self.login_handler.states[self.state.HUB] = [self.committee_hub.handler]
    async def password_access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="What is your one time password?")
        return self.state.VERIFICATION

    async def verify_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        committee_name = password.split(':')[0]
        try:
            committee_command = [key for key in committees.keys() if committees[key] == committee_name][0]
        except IndexError:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
            return self.state.HOME
        if not bx_utils.db.use_one_time_pass(password, committee_name):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
            return self.state.HOME
        result = bx_utils.db.add_access_rights(update.effective_user, committee_name, committee_command)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Your rights have been successfully updated")
        return self.state.HOME

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(COMMITTEES_TOKEN).build()
    committees_hub = Committees_Login()
    application.add_handler(committees_hub.login_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()