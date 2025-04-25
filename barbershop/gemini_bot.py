import os
import re
from datetime import datetime, timedelta
import logging
from langchain.schema import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .models import HairService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Gemini API key
os.environ["GOOGLE_API_KEY"] = "YOUR API KEY"

# Get all services as string
def get_all_services_text():
    services = HairService.objects.all()
    return "\n".join([f"{s.name}: ${s.price}" for s in services])

# Extract time and date from user input
def extract_time_from_input(user_input):
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', user_input.lower())
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)

        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0

        # Check if the user mentioned "tomorrow"
        base_date = datetime.now()
        if "tomorrow" in user_input.lower():
            base_date = base_date + timedelta(days=1)

        appointment_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        logger.info(f"Extracted appointment time: {appointment_time}")
        return appointment_time
    return None

# Book appointment on Google Calendar
def book_appointment_on_calendar(summary, start_time):
    scopes = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = 'app.json'  # Path to your service account JSON file
    calendar_id = 'shahisamrat711@gmail.com'  # Use 'primary' or your specific calendar ID

    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes
        )
        service = build('calendar', 'v3', credentials=credentials)

        # Calculate end time of the appointment (1 hour slot)
        end_time = start_time + timedelta(hours=1)
        logger.info(f"Checking availability from {start_time} to {end_time}")

        # Step 1: List events in the time range to confirm they exist
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        logger.info(f"Events in the time range: {events}")

        # Step 2: Check availability using freebusy query
        freebusy_query = {
            "timeMin": start_time.isoformat() + 'Z',  # The start time in UTC
            "timeMax": end_time.isoformat() + 'Z',  # The end time in UTC
            "timeZone": 'Asia/Kathmandu',  # Timezone for the query
            "items": [{"id": calendar_id}]
        }

        busy_result = service.freebusy().query(body=freebusy_query).execute()
        busy_times = busy_result['calendars'][calendar_id].get('busy', [])
        logger.info(f"Freebusy query result: {busy_result}")
        logger.info(f"Busy times: {busy_times}")

        # If the time slot is busy, suggest the next available time slot
        if busy_times:
            next_available = end_time
            for _ in range(5):  # Check the next 5 hours for availability
                new_end = next_available + timedelta(hours=1)
                new_query = {
                    "timeMin": next_available.isoformat() + 'Z',
                    "timeMax": new_end.isoformat() + 'Z',
                    "timeZone": 'Asia/Kathmandu',
                    "items": [{"id": calendar_id}]
                }

                result = service.freebusy().query(body=new_query).execute()
                if not result['calendars'][calendar_id].get('busy', []):
                    # If slot is available, return suggestion for the next available time
                    return f"That time is already booked. How about {next_available.strftime('%I:%M %p')} on {next_available.strftime('%Y-%m-%d')}?"

                # Move to the next available hour if the slot is still busy
                next_available += timedelta(hours=1)

            return "Sorry, no available slots in the next few hours."

        # Step 3: Book the event only if the time is free
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Asia/Kathmandu',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Asia/Kathmandu',
            },
        }

        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return f"Your appointment is booked at {start_time.strftime('%I:%M %p')} on {start_time.strftime('%Y-%m-%d')}. Please come on time."

    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return f"Error booking appointment: {str(e)}"

# Main bot response
def get_bot_response(user_input):
    services_text = get_all_services_text()

    system_prompt = SystemMessage(content=f"""
You are a helpful barbershop assistant. Only answer questions about:
- Haircuts
- Beard trims
- Grooming
- Appointments
- Shop hours, etc.

Here are the current services and prices:\n{services_text}

If asked anything unrelated, reply with:
"I'm here to assist with barbershop-related questions only. How can I help with your grooming needs?"
""")

    chat = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    messages = [
        system_prompt,
        HumanMessage(content=user_input)
    ]
    response = chat.invoke(messages)  # Updated to use invoke instead of __call__

    # Try to book appointment if time is mentioned
    appointment_time = extract_time_from_input(user_input)
    if appointment_time:
        result = book_appointment_on_calendar("Barbershop Appointment", appointment_time)
        return result  # Return the result directly (success message or suggestion)

    return response.content