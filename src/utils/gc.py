from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import json
from dotenv import load_dotenv
import os
from utils import config
import datetime

load_dotenv()
EVENT_CALENDAR_ID = os.getenv("EVENT_CALENDAR_ID")
DEADLINE_CALENDAR_ID = os.getenv("DEADLINE_CALENDAR_ID")
# The scopes define the level of access your bot will have to the shared calendar.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Path to the service account key JSON file.
SERVICE_ACCOUNT_KEY_PATH = config.ROOT + '/../service_account.json'
def get_calendar_service():
    # Load the service account credentials from the JSON key file.
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY_PATH, scopes=SCOPES)

    # Create the Calendar API client using the service account credentials.
    service = build("calendar", "v3", credentials=credentials)
    return service

def format_date(date_obj):
    # If object is a string convert it to a date object
    if type(date_obj) == type(''):
        date_obj = datetime.datetime.strptime(date_obj, '%Y-%m-%d').date()

    # Get the day of the week (e.g., Monday, Tuesday, etc.)
    day_of_week = date_obj.strftime("%A")

    # Get the day of the month with suffix (e.g., 1st, 2nd, 3rd, 4th, etc.)
    day_of_month = date_obj.strftime("%d")
    day_of_month = day_of_month if day_of_month[0] != '0' else day_of_month[1]
    suffix = "th" if 11 <= int(day_of_month) % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(int(day_of_month) % 10, "th")

    # Get the month (e.g., January, February, etc.)
    month = date_obj.strftime("%B")

    # Combine the parts to create the formatted date string
    formatted_date = f"{day_of_week} {day_of_month}{suffix} of {month}"

    return formatted_date

def changeDate(formatted_time, new_date):
    date, time = formatted_time.split('T')
    return str(new_date)+ 'T'+ time

def nextDay(formatted_time):
    date, time = formatted_time.split('T')
    date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
    date_obj = date_obj + datetime.timedelta(days=1)
    date = str(date_obj)
    return date + 'T' + time

def changeTime(formatted_time, new_time, next_day):
    date, time = formatted_time.split('T')
    if next_day:
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        date_obj = date_obj + datetime.timedelta(days=1)
        date = str(date_obj)
    return date + 'T' + new_time + ':00'

def deleteEvent(event, deadline=False):
    if deadline:
        calendar_id = DEADLINE_CALENDAR_ID
    else:
        calendar_id = EVENT_CALENDAR_ID
    service = get_calendar_service()
    service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()

def timeFormat(date, time):

    return str(date) + 'T' + time + ':00'

def create_event(date, startTime, endTime, committee, name, description, deadline = False):
    if deadline:
        calendar_id = DEADLINE_CALENDAR_ID
    else:
        calendar_id = EVENT_CALENDAR_ID
    service = get_calendar_service()
    startDate = timeFormat(date, startTime)
    if endTime < startTime:
        endDate = timeFormat(date + datetime.timedelta(days=1), endTime)
    else:
        endDate = timeFormat(date, endTime)
    event_data={
        "summary": name,
        "description": description,
        "start": {
            "dateTime": startDate,
            "timeZone": "Europe/Paris",
        },
        "end": {
            "dateTime": endDate,
            "timeZone": "Europe/Paris",
        },
        "extendedProperties": {
            "shared": {
                "committee": committee
            }
        },
        "colorId": color_from_committee(committee)
    }
    # Use the service to create an event in the shared calendar.
    event = service.events().insert(calendarId=calendar_id, body=event_data).execute()
    return event

def get_events(deadline=False):
    if deadline:
        calendar_id = DEADLINE_CALENDAR_ID
    else:
        calendar_id = EVENT_CALENDAR_ID
    service = get_calendar_service()
    # Use the service to retrieve events from the shared calendar.
    events_result = service.events().list(calendarId=calendar_id).execute()
    events = events_result.get("items", [])
    return events

def get_committee_events(committee, time_max=None):
    """
    Gets the events created by a given committee, if a max_time is given events are limited to that time
    """
    service = get_calendar_service()
    now = datetime.datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    query_params = {}
    if time_max is not None:
        query_params['timeMax'] = time_max
    events_result = service.events().list(calendarId=EVENT_CALENDAR_ID, timeMin=time_min, **query_params).execute()
    committee_events = [
        event for event in events_result['items']
        if event.get('extendedProperties', {}).get('shared', {}).get('committee') == committee
    ]
    return committee_events

COLOR_ID = {'Lavender': '1',
          'Sage': '2',
          'Grape':'3',
          'Flamingo': '4',
          'Banana': '5',
          'Tangerine': '6',
          'Peacock': '7',
          'Graphite': '8',
          'Blueberry': '9',
          'Basil': '10',
          'Tomato': '11'
          }

def update_event(event_data, deadline = False):
    """
    Updates an event given its event data
    """
    if deadline:
        calendar_id = DEADLINE_CALENDAR_ID
    else:
        calendar_id = EVENT_CALENDAR_ID
    event_id = event_data["id"]
    service = get_calendar_service()
    service.events().update(calendarId=calendar_id, eventId=event_id, body=event_data).execute()

def color_from_committee(committee_name):
    """
    A simple hash from the committee_name to a number from 0 to 11 which represents the color of the event in the calendar
    """
    value = 0
    for character in committee_name:
        value += ord(character)
    colorID = value%12
    return str(colorID)

def event_presentation_from_api(event_data):
    committee = event_data["extendedProperties"]["shared"]["committee"]
    name = event_data["summary"]
    description = event_data["description"]
    date, start_time = event_data["start"]["dateTime"].split('T')
    _ , end_time = event_data["end"]["dateTime"].split('T')
    start = start_time[:5]
    end = end_time[:5]
    return event_presentation_from_data(date, name, start, end, description)
def event_presentation_from_data(date, name, start, end, description):
    return f"<b>{name}</b> on the {format_date(date)} {start}-{end}\n{description}"
