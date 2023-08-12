import logging
import json
import random
import string
import telegram.error
import enum

from telegram_bot_calendar import WYearTelegramCalendar, LSTEP
from utils import db, gc
import utils

utils.Vcheck.telegram()
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

with open(utils.config.ROOT + '/data/Committees/committees.json') as f:
    committees = json.load(f)

utils.logger(__name__)

class Activity(enum.Enum):
    HOME = 1
    LOGIN = 2
    VERIFICATION = 3
    HUB = 4
    MESSAGE = 5
    MESSAGE_CONFIRMATION = 16
    ACCESS = 6
    RIGHTS = 7
    EVENT = 8
    DATE = 9
    START_TIME = 10
    END_TIME = 11
    NAME = 12
    SUMMARY = 13
    CONFIRMATION_EVENT = 14
    MODIFY_EVENT = 15
class Right_changer:
    class State(enum.Enum):
        USER = 1
        ROLE = 2
        CONFIRMATION = 3
        MORE = 4
    def __init__(self, user_rights):
        self.user_rights = user_rights
        self.active_user = [user for user in user_rights.keys() if user_rights[user] == 'Prez'][0]
        self.keyboard = InlineKeyboardMarkup([[]])
        self.state = self.State.USER
        self.new_user_rights = user_rights
        self.params = {}

    def build(self):
        if self.state == self.State.USER:
            self._build_users()
        if self.state == self.State.ROLE:
            self._build_role()
        if self.state == self.State.CONFIRMATION:
            self._build_confirmation()
        if self.state == self.State.MORE:
            self._build_more()

    def process(self, call_data):
        # callback = user_role_confirmation_more
        params = call_data.split('_')
        params = dict(zip(['user', 'role', 'confirmation', 'more'][:len(params)], params))
        self.params = params
        if len(params) == 1:
            self.state = self.State.ROLE
            return False, 'role', None
        elif len(params) == 2:
            self.state = self.State.CONFIRMATION
            return False, 'confirm', None
        elif len(params) == 3:
            if params['confirmation'] == 'yay':
                self.new_user_rights[self.params['user']] = self.params['role']
                if self.params['role'] == 'Prez':
                    self.new_user_rights[self.active_user] = 'Admin'
                self.state = self.State.MORE
                return True, 'more', self.new_user_rights
            self.state = self.State.MORE
            return False, 'more', None
        elif len(params) == 4:
            if params['more'] == 'yay':
                self.user_rights = self.new_user_rights
                self.state = self.State.USER
                return True, 'user', None
            return False, 'user', None

    def _build_users(self):
        user_list = [[user] for user in self.user_rights.keys() if user != self.active_user]
        self.keyboard = self._build_keyboard(user_list)

    def _build_role(self):
        roles = [['Prez'], ['Admin'], ['Comms'], ['Events'], ['None']]
        self.keyboard = self._build_keyboard(roles)

    def _build_confirmation(self):
        confirmation = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(confirmation)

    def _build_more(self):
        more = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(more)

    def _build_keyboard(self, elements):
        keyboard = []
        for i, row in enumerate(elements):
            keyboard.append([])
            for element in row:
                callback = self._build_callback(element)
                keyboard[i].append(InlineKeyboardButton(element, callback_data=callback))
        return InlineKeyboardMarkup(keyboard)

    def _build_callback(self, element):
        if self.state == self.State.USER:
            return element
        if self.state == self.State.ROLE:
            return f'{self.params["user"]}_{element}'
        if self.state == self.State.CONFIRMATION:
            return f'{self.params["user"]}_{self.params["role"]}_{element}'
        if self.state == self.State.MORE:
            return f'{self.params["user"]}_{self.params["role"]}_{self.params["confirmation"]}_{element}'

class time_picker:
    class State(enum.Enum):
        HOUR = 1
        MINUTES = 2
    def __init__(self):
        self.hour = None
        self.keyboard = InlineKeyboardMarkup([[]])
        self.state = self.State.HOUR

    def build(self):
        if self.state == self.State.HOUR:
            self.create_hours_keyboard()
        if self.state == self.State.MINUTES:
            self.create_minutes_keyboard()

    def process(self, data):
        if self.hour is None:
            self.hour = data
            self.state = self.State.MINUTES
            return False, None
        else:
            self.hour = None
            self.state = self.State.HOUR
            return True, data


    def create_minutes_keyboard(self):
        keyboard = [[]]
        hour = self.hour
        times = [hour + ':00', hour + ':15', hour + ':30', hour + ':45']
        for time in times:
            keyboard[0].append(InlineKeyboardButton(time, callback_data=time))
        self.keyboard = InlineKeyboardMarkup(keyboard)

    def create_hours_keyboard(self):
        keyboard = []
        hours = [str(i).zfill(2) for i in range(0, 24)]

        for i in range(0, 24, 6):
            row = []
            for j in range(6):
                hour = hours[i + j]
                row.append(InlineKeyboardButton(hour, callback_data=hour))
            keyboard.append(row)
        self.keyboard = InlineKeyboardMarkup(keyboard)

class event_changer:
    class State(enum.Enum):
        EVENT = 1
        PROPERTY = 2
        VALUE = 3
        MORE = 4
        OTHER_EVENT = 5
    def __init__(self, events):
        self.events = events
        self.event = None
        self.params = {}
        self.property = None
        self.state = self.State.OTHER_EVENT

    def build(self):
        if self.state == self.State.EVENT:
            self._build_events()
        elif self.state == self.State.PROPERTY:
            self._build_properties()
        elif self.state == self.State.MORE:
            self._build_more()
        elif self.state == self.State.OTHER_EVENT:
            self._build_other_event()

    def process(self, call_data):
        if self.state == self.State.OTHER_EVENT:
            if call_data == 'yay':
                self.state = self.State.EVENT
                return True, 'event', None
            return False, 'event', None
        if self.state == self.State.EVENT:
            self.state = self.State.PROPERTY
            self.event = [event for event in self.events if event["summary"] == call_data][0]
            return True, 'property', None
        if self.state == self.State.PROPERTY:
            if call_data == 'Delete Event':
                self.state = self.State.OTHER_EVENT
                return False, 'delete', self.event
            self.state = self.State.VALUE
            self.property = call_data
            return True, 'value', None
        if self.state == self.State.VALUE:
            self.state = self.State.MORE
            self.change(self.property, call_data)
            return True, 'more', None
        if self.state == self.State.MORE:
            if call_data == 'yay':
                self.state = self.State.PROPERTY
                return True, 'property', None
            self.state = self.State.OTHER_EVENT
            self.check_dates()
            return False, 'other', self.event

    def _build_events(self):
        event_names = [[event_data['summary']] for event_data in self.events]
        self.keyboard = self._build_keyboard(event_names)

    def _build_properties(self):
        properties = [['Date'], ['Start'], ['End'], ['Name'], ['Description'], ['Delete Event']]
        self.keyboard = self._build_keyboard(properties)

    def _build_more(self):
        more = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(more)

    def _build_other_event(self):
        other = [['yay', 'nay']]
        self.keyboard = self._build_keyboard(other)

    def _build_keyboard(self, elements):
        keyboard = []
        for i, row in enumerate(elements):
            keyboard.append([])
            for element in row:
                keyboard[i].append(InlineKeyboardButton(element, callback_data=element))
        return InlineKeyboardMarkup(keyboard)

    def change(self, property_changed, data):
        if property_changed == 'Name':
            self.event["summary"] = data
        if property_changed == 'Description':
            self.event["description"] = data
        if property_changed == 'Date':
            self.event["start"]["dateTime"] = gc.changeDate(self.event["start"]["dateTime"], data)
            self.event["end"]["dateTime"] = gc.changeDate(self.event["end"]["dateTime"], data)
        if property_changed == 'Start':
            self.event["start"]["dateTime"] = gc.changeTime(self.event["start"]["dateTime"], data, False)
        if property_changed == 'End':
            self.event["end"]["dateTime"] = gc.changeTime(self.event["end"]["dateTime"], data, False)

    def check_dates(self):
        if self.event["end"]["dateTime"]  < self.event["start"]["dateTime"]:
            self.event["end"]["dateTime"] = gc.nextDay(self.event["end"]["dateTime"])

class Event_handler:
    def __init__(self, active_committee, ):
        self.state = Activity.EVENT
        self.active_committee = active_committee
        self.date = ''
        self.start_time = ''
        self.end_time = ''
        self.name = ''
        self.user_rights = ''
        self.description = ''
        self.getting_data = False
        self.time_picker = time_picker()
        self.event_changer = None
        self.event_handler = ConversationHandler(
            entry_points=[CommandHandler("event", self.events)],
            states={
                self.state.EVENT: [CommandHandler("view", self.view), CommandHandler("create", self.create)],
                self.state.DATE: [CallbackQueryHandler(self.date_selection)],
                self.state.START_TIME: [CallbackQueryHandler(self.select_start)],
                self.state.END_TIME: [CallbackQueryHandler(self.select_end)],
                self.state.NAME: [MessageHandler(filters.TEXT, self.naming)],
                self.state.SUMMARY: [MessageHandler(filters.TEXT, self.summary)],
                self.state.CONFIRMATION_EVENT: [CallbackQueryHandler(self.confirmation)],
                self.state.MODIFY_EVENT: [CallbackQueryHandler(self.modify_event), MessageHandler(filters.TEXT, self.modify_event)]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.back)],
            map_to_parent={
                self.state.HUB: self.state.HUB,
            }
        )
    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You are back to the hub")
        return self.state.HUB

    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_rights == 'Comms':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to /create a new event or to /view the already added events")
        return self.state.EVENT

    async def view(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        events = gc.get_committee_events(self.active_committee)
        event_descriptions = []
        for item in events:
            event_descriptions.append(gc.event_presentation_from_api(item))
        message = '\n -------------------------------------- \n'.join(event_descriptions)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="The events already planned by your committee are:")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message,
                                       parse_mode=ParseMode.HTML)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to change any of these events?",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('yay', callback_data='yay')], [InlineKeyboardButton('nay', callback_data='nay')]]))
        self.event_changer = event_changer(events)
        return self.state.MODIFY_EVENT

    async def modify_event(self, update: Update, context: CallbackContext):
        if self.event_changer.property in ['Name', 'Description'] and self.getting_data:
            data = update.message.text
            self.getting_data = False
        else:
            query = update.callback_query
            await query.answer()
            data = query.data
        if self.event_changer.property == 'Date' and self.getting_data:
            ##Handles the date selection
            result, key, step = WYearTelegramCalendar().process(data)
            if not result and key:
                await query.edit_message_text(f"Enter the new date", reply_markup=key)
                context.user_data["step"] = step  # Update the step in user_data
                return self.state.MODIFY_EVENT
            elif result:
                await query.edit_message_text(text=f'Selected {data}')
                data = result
                self.getting_data = False

        if self.event_changer.property == 'Start' and self.getting_data:
            key, result = self.time_picker.process(data)
            self.time_picker.build()
            if result is None:
                await query.edit_message_text(text='Enter the new starting time',
                                              reply_markup=self.time_picker.keyboard)
                return self.state.MODIFY_EVENT
            else:
                await query.edit_message_text(text=f'Selected {data}')
                data = result
                self.getting_data = False

        if self.event_changer.property == 'End' and self.getting_data:
            key, result = self.time_picker.process(data)
            self.time_picker.build()
            if result is None:
                await query.edit_message_text(text='Enter the new ending time',
                                              reply_markup=self.time_picker.keyboard)
                return self.state.MODIFY_EVENT
            else:
                data = result
                await query.edit_message_text(text=f'Selected {data}')
                self.getting_data = False



        key, state, event = self.event_changer.process(data)
        if not key and state == 'delete':
            gc.deleteEvent(event)
            await query.edit_message_text(text="Alright")
            return self.state.HUB
        if not key and state == 'event':
            await query.edit_message_text(text="Alright")
            return self.state.HUB
        message = {'event': 'Which event do you want to modify?', 'property': 'Which property do you want to change?',
                   'more': 'Do you want to change other properties', 'other': 'Changes saved\nDo you want to change another event?'}
        if key and state == 'more':
            self.event_changer.build()
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=message[state], reply_markup=self.event_changer.keyboard)
            return self.state.MODIFY_EVENT

        if not key and state == 'other':
            self.event_changer.build()
            gc.update_event(event)
            await query.edit_message_text(text=message[state], reply_markup=self.event_changer.keyboard)
            return self.state.MODIFY_EVENT

        if key and state != 'value':
            self.event_changer.build()
            await query.edit_message_text(text=message[state], reply_markup=self.event_changer.keyboard)
            return self.state.MODIFY_EVENT
        property_to_change = self.event_changer.property
        self.getting_data = True
        if property_to_change in ['Name', 'Description']:
            await query.edit_message_text(text=f"Enter the new {property_to_change.lower()}")
            return self.state.MODIFY_EVENT
        if property_to_change == 'Date':
            calendar, step = WYearTelegramCalendar().build()
            await query.edit_message_text(text=f"Enter the new date", reply_markup=calendar)
            return self.state.MODIFY_EVENT
        if property_to_change == 'Start':
            self.time_picker.build()
            await query.edit_message_text(text="Enter the new starting time",
                                          reply_markup=self.time_picker.keyboard)
            return self.state.MODIFY_EVENT
        if property_to_change == 'End':
            self.time_picker.build()
            await query.edit_message_text(text="Enter the new ending time",
                                          reply_markup=self.time_picker.keyboard)
            return self.state.MODIFY_EVENT



    async def create(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        calendar, step = WYearTelegramCalendar().build()

        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="When do you want to create an event?",
                                       reply_markup=calendar)
        return self.state.DATE

    async def date_selection(self, update: Update, context: CallbackContext):
        query = update.callback_query
        data = query.data

        result, key, step = WYearTelegramCalendar().process(data)

        if not result and key:
            await query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)
            context.user_data["step"] = step  # Update the step in user_data
            return self.state.DATE
        elif result:
            await query.edit_message_text(f"You selected the date {result}")
            self.date = result
            self.time_picker.build()

            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="At what time does your event start?",
                                           reply_markup=self.time_picker.keyboard)
            return self.state.START_TIME

    async def select_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key, result = self.time_picker.process(query.data)
        self.time_picker.build()
        if result is None:
            await query.edit_message_text(text='At what time does your event start?',
                                          reply_markup=self.time_picker.keyboard)
            return self.state.START_TIME
        self.start_time = result
        await query.edit_message_text(text=f'Selected {self.start_time}')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="When does it end?",
                                       reply_markup=self.time_picker.keyboard)
        return self.state.END_TIME

    async def select_end(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        key, result = self.time_picker.process(query.data)
        self.time_picker.build()
        if result is None:
            await query.edit_message_text(text='When does it end?',
                                          reply_markup=self.time_picker.keyboard)
            return self.state.END_TIME
        self.end_time = result
        await query.edit_message_text(text=f'Selected {self.end_time}')
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Give it a name")
        return self.state.NAME

    async def naming(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.name = update.message.text
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Give a brief description of your event")
        return self.state.SUMMARY

    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.description = update.message.text
        event_description = gc.event_presentation_from_data(self.active_committee, self.date, self.name, self.start_time, self.end_time, self.description)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Current Event:\n {event_description}",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('yay', callback_data='True'), InlineKeyboardButton('nay', callback_data='False')]]),
                                       parse_mode=ParseMode.HTML)
        return self.state.CONFIRMATION_EVENT

    async def confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        if query.data == 'False':
            await query.edit_message_text(text="Event upload cancelled")
            return self.state.HUB
        await query.edit_message_text(text=f"The event has been uploaded to the google calendar, users will be able to see it on your committee part of SailoreBXBot two weeks prior to the event")
        gc.create_event(self.date, self.start_time, self.end_time, self.active_committee, self.name, self.description)
        return self.state.HUB

class Access_handler:
    def __init__(self, active_committee):
        self.active_committee = active_committee
        access_granted = db.get_committee_access(self.active_committee)
        keys = ['user:' + user_id for user_id in access_granted.keys()]
        admins_info = db.get_users_info(keys)
        self.admins_rights = {admin['name']: access_granted[admin['id']] for admin in admins_info}
        self.admins_ids = {admin['name']: admin['id'] for admin in admins_info}
        self.state = Activity.ACCESS
        self.access_list = []
        self.user_rights = None
        self.right_changer = Right_changer(self.admins_rights)
        self.access_handler=ConversationHandler(
            entry_points=[CommandHandler("access", self.access)],
            states={
                self.state.ACCESS: [
                    CommandHandler("password", self.password),
                    CommandHandler("rights", self.rights),
                    CommandHandler("back", self.back)
                ],
                self.state.RIGHTS: [
                    CallbackQueryHandler(self.chose_role)
                ],
            },
            fallbacks=[MessageHandler(filters.TEXT, self.access)],
            map_to_parent={
                self.state.HUB: self.state.HUB
            }
        )

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You are back to the hub")
        return self.state.HUB
    async def access(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.user_rights == 'Prez':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        roles = ["Prez: All functionalities + access management", "Admin: All functionalities", "Comms: Message functionality", "Events: Events functionality"]
        current_admins = [f"{key}: {value}" for key, value in self.admins_rights.items()]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Inside any committee hub the following roles are allowed: \n" + '\n'.join(roles))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="The current users with access are: \n" + '\n'.join(current_admins))
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to generate a one-time /password to register a new user or change the current /rights (you can also go /back to the hub)")
        return self.state.ACCESS
    async def password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        new_password=self.active_committee + ':' + ''.join(random.choices(string.digits + string.ascii_letters, k=10))
        db.add_one_time_pass(new_password, self.active_committee)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"The password generated is <b>{new_password}</b>, the default rights are admin for new users",
                                       parse_mode=ParseMode.HTML)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"This password only has one use, send it to the person you want to give access")
        return self.state.HUB
    async def rights(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.right_changer = Right_changer(self.admins_rights)
        self.right_changer.build()
        keyboard = self.right_changer.keyboard
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Who's right do you want to change?",
                                       reply_markup=keyboard)
        return self.state.RIGHTS
    async def chose_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        await query.answer()
        data = query.data
        result, state, rights = self.right_changer.process(data)
        if result and state=='more':
            #save the changes
            self.admins_rights = self.right_changer.new_user_rights
        if not result and state=='user':
            if 'None' in self.admins_rights.values():
                users_to_eliminate = [user for user in self.admins_rights.keys() if self.admins_rights[user] == 'None']
                for user in users_to_eliminate:
                    del self.admins_rights[user]
                    committee_command = committees[self.active_committee]["command"]
                    db.eliminate_access_rights(self.admins_ids[user], self.active_committee, committee_command)
            new_rights = {self.admins_ids[admin]: self.admins_rights[admin] for admin in self.admins_rights.keys()}
            db.change_committee_access(self.active_committee, new_rights)
            await query.edit_message_text(text="The rights have been updated accordingly")
            return self.state.HUB
        self.right_changer.build()
        keyboard = self.right_changer.keyboard
        params = data.split('_')
        message = {'user': "Who's right do you want to change?", 'role': "Which role do you want to apply? \n (Selecting Prez will change your role to Admin)", 'confirm': f"Confirm the change of {params[0]} to {params[-1]}", 'more': "Do you want to make any other changes"}
        await query.edit_message_text(text=message[state], reply_markup=keyboard)
        return self.state.RIGHTS

class Message_handler:
    def __init__(self, active_committee):
        self.active_committee = active_committee
        self.state = Activity.MESSAGE
        self.user_rights = None
        self.message_text = ''

        self.message_handler = ConversationHandler(
            entry_points=[CommandHandler("message", self.message)],
            states={
                self.state.MESSAGE: [MessageHandler(filters.TEXT, self.confirm)],
                self.state.MESSAGE_CONFIRMATION: [CallbackQueryHandler(self.parrot)]
            },
            fallbacks=[MessageHandler(filters.TEXT, self.back)],
            map_to_parent={
                self.state.HUB: self.state.HUB
            }
        )
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_rights == 'Events':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="What message do you wish to send to your subscriptors?")
        return self.state.MESSAGE

    async def confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.message_text = update.message.text
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('yay', callback_data='yay')],
            [InlineKeyboardButton('nay', callback_data='nay')]
        ])
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Do you want to parrot this message to all your subs?",
                                       reply_markup= reply_markup)
        return self.state.MESSAGE_CONFIRMATION

    async def parrot(self, update: Update, context: CallbackContext):
        query = update.callback_query
        await query.answer()
        if query.data == 'nay':
            await query.edit_message_text(text='Alright, back to the hub')
            return self.state.HUB

        keys = db.subs_of_committee(self.active_committee)
        users_info = db.get_users_info(keys)
        parrot_bot = Bot(PARROT_TOKEN)
        sailore_bot = Bot(SAILORE_TOKEN)
        counter = 0
        for user in users_info:
            try:
                await parrot_bot.send_message(chat_id=user['id'],
                                               text=f'Hello {user["name"]}, this is a communication from {self.active_committee}:')
                await parrot_bot.send_message(chat_id=user['id'], text=self.message_text)
            except telegram.error.BadRequest:
                counter += 1
                await sailore_bot.send_message(chat_id=user['id'],
                    text=f"""Hello {user['name']}, a communication from one of your subscriptions was just sent to you but you didn't receive it as you haven't signed in into t.me/SailoreParrotBot""")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successfully echoed your message")
        if counter > 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"We also notified {counter} of your users which didn't sign into @SailoreParrotBot")
        return self.state.HUB

    async def back(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="You are back to the hub")
        return self.state.HUB

class Committee_hub:
    def __init__(self, active_committee):
        self.active_committee = active_committee
        self.state = Activity.HUB
        self.access_handler = Access_handler(active_committee)
        self.event_handler = Event_handler(active_committee)
        self.message_handler = Message_handler(active_committee)
        self.user_rights = None
        hub_handlers = [CommandHandler("subs", self.give_subs),
                        self.message_handler.message_handler,
                        self.event_handler.event_handler,
                        self.access_handler.access_handler,
                        CommandHandler("logout", self.logout),
                        MessageHandler(filters.TEXT, self.hub)]
        self.committee_handler=ConversationHandler(
            entry_points=hub_handlers,
            states={
                self.state.HUB: hub_handlers,
                self.state.MESSAGE: [MessageHandler(filters.TEXT, self.parrot)],
            },
            fallbacks=[MessageHandler(filters.TEXT, self.hub)],
            map_to_parent={
                self.state.HOME: self.state.HOME
            }
        )
    async def hub(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_rights = db.get_committee_access(self.active_committee)[str(update.effective_user.id)]
        self.access_handler.user_rights = self.user_rights
        self.event_handler.user_rights = self.user_rights
        self.message_handler.user_rights = self.user_rights
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"You are logged into {self.active_committee} as {self.user_rights}")
        if self.user_rights == 'Prez':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subs, send them a /message, upload an /event to the google calendar or manage the /access to this committee hub")
        elif self.user_rights == 'Admin':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subs, send them a /message or upload an /event to the google calendar")
        elif self.user_rights == 'Comms':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subs or send them a /message")
        elif self.user_rights == 'Events':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="From here you can check your /subs or upload an /event to the google calendar")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="If you want to access other committee, then /logout")
        return self.state.HUB
    async def give_subs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keys = db.subs_of_committee(self.active_committee)
        users_info = db.get_users_info(keys)
        names = [user["fullname"] for user in users_info]

        names.insert(0, '')
        name_list = '\n - '.join(names)
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text=f"Your committee has a total of {len(names) - 1} subs")
        if len(names) > 1:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="This is the full list:" + name_list)
        return self.state.HUB
    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_rights == 'Events':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="What message do you wish to send to your subscriptors?")
        return self.state.MESSAGE
    async def parrot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message.text
        keys = db.subs_of_committee(self.active_committee)
        users_info = db.get_users_info(keys)
        parrot_bot = Bot(PARROT_TOKEN)
        sailore_bot = Bot(SAILORE_TOKEN)
        counter = 0
        for user in users_info:
            try:
                await parrot_bot.send_message(chat_id=user['id'],
                                               text=f'Hello {user["name"]}, this is a communication from {self.active_committee}:')
                await parrot_bot.send_message(chat_id=user['id'], text=message)
            except telegram.error.BadRequest:
                counter += 1
                await sailore_bot.send_message(chat_id=user['id'],
                    text=f"""Hello {user['name']}, a communication from one of your subscriptions was just sent to you but you didn't receive it as you haven't signed in into t.me/SailoreParrotBot""")
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successfully echoed your message")
        if counter > 0:
            await context.bot.send_message(chat_id=update.effective_user.id,
                                           text=f"We also notified {counter} of your users which didn't sign into @SailoreParrotBot")
        return self.state.HUB
    async def event(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self.user_rights == 'Comms':
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="You don't have access rights for this functionality")
            return self.state.HUB
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Functionality to be implemented")
    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_user.id,
                                       text="Successful logout")
        return self.state.HOME

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
        info = db.get_user_info(update.effective_user)
        rights = info["rights"]
        access_list = db.db_to_list(rights)
        message_list = db.list_to_telegram(access_list)
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
        Update the info about the committee name in all handlers
        """
        self.committee_hub = Committee_hub(self.active_committee)
        self.login_handler.states[self.state.HUB] = [self.committee_hub.committee_handler]
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
        if not db.use_one_time_pass(password, committee_name):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="Error: either you entered an incorrect password or one has not been generated")
            return self.state.HOME
        result = db.add_access_rights(update.effective_user, committee_name, committee_command)
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