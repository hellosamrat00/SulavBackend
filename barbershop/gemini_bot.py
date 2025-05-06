import os
import re
from datetime import datetime, timedelta
import logging
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .models import HairService, Booking, FAQ
from langchain.schema import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langdetect import detect, DetectorFactory
from google.cloud import translate_v2 as translate


DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

os.environ["GOOGLE_API_KEY"] = ""

try:
    translate_client = translate.Client.from_service_account_json(os.path.join(settings.BASE_DIR, 'app.json'))
except Exception as e:
    logger.warning(f"Google Translate client initialization failed: {str(e)}. Falling back to English.")
    translate_client = None

def translate_text(text, target_language):
    if not translate_client or target_language == 'en':
        return text
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result['translatedText']
    except Exception as e:
        logger.error(f"Translation failed: {str(e)}")
        return text

def get_all_services_text(language='en'):
    services = HairService.objects.all()
    services_text = "\n".join([f"{s.name}: ${s.price}" for s in services])
    return translate_text(services_text, language)

def extract_time_from_input(user_input, language='en'):
    """Extract time from user input, supporting multilingual formats."""
    user_input_lower = user_input.lower()

    # English AM/PM format (e.g., "3 PM", "3:30 pm")
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', user_input_lower)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)
        if am_pm == 'pm' and hour != 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0
    else:
        # 24-hour format (e.g., "15:00", "15h30")
        match = re.search(r'(\d{1,2})(?::|h)?(\d{2})?', user_input_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            if hour > 23 or minute > 59:
                return None
        else:
            # Language-specific time expressions (e.g., "tres de la tarde")
            time_phrases = {
                'es': [
                    (r'tres\s*de\s*la\s*tarde', 15, 0),  # "tres de la tarde" -> 3 PM
                    (r'cuatro\s*de\s*la\s*mañana', 4, 0),  # "cuatro de la mañana" -> 4 AM
                ],
                'fr': [
                    (r'quinze\s*heures', 15, 0),  # "quinze heures" -> 3 PM
                    (r'dix\s*heures', 10, 0),  # "dix heures" -> 10 AM
                ],
            }
            for lang, phrases in time_phrases.items():
                if lang == language:
                    for pattern, h, m in phrases:
                        if re.search(pattern, user_input_lower):
                            hour, minute = h, m
                            break
                    else:
                        return None
                    break
            else:
                return None

    # Determine date (today or tomorrow)
    tomorrow_keywords = {
        'en': ['tomorrow'],
        'es': ['mañana'],
        'fr': ['demain'],
        # Add more languages
    }
    base_date = datetime.now()
    for lang, keywords in tomorrow_keywords.items():
        if lang == language and any(keyword in user_input_lower for keyword in keywords):
            base_date += timedelta(days=1)
            break

    try:
        appointment_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        logger.info(f"Extracted appointment time: {appointment_time} for input: {user_input}")
        return appointment_time
    except ValueError as e:
        logger.error(f"Invalid time extracted: {str(e)}")
        return None

def book_appointment_on_calendar(summary, start_time, user, language='en'):
    logger.info(f"Booking for user: {user}, Authenticated: {user.is_authenticated}")
    
    if not user.is_authenticated:
        error_message = "You need to log in to book an appointment. Please log in and try again."
        logger.info("Unauthenticated booking attempt")
        return translate_text(error_message, language)

    scopes = ['https://www.googleapis.com/auth/calendar']
    SERVICE_ACCOUNT_FILE = os.path.join(settings.BASE_DIR, 'app.json')
    calendar_id = 'shahisamrat711@gmail.com'
    
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            logger.error(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
            error_message = "Error: Service account configuration is missing. Contact the administrator."
            return translate_text(error_message, language)
        
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes
        )
        service = build('calendar', 'v3', credentials=credentials)
        end_time = start_time + timedelta(hours=1)
        logger.info(f"Checking availability from {start_time} to {end_time}")

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat() + 'Z',
            timeMax=end_time.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        logger.info(f"Events in the time range: {events}")

        freebusy_query = {
            "timeMin": start_time.isoformat() + 'Z',
            "timeMax": end_time.isoformat() + 'Z',
            "timeZone": 'Asia/Kathmandu',
            "items": [{"id": calendar_id}]
        }

        busy_result = service.freebusy().query(body=freebusy_query).execute()
        busy_times = busy_result['calendars'][calendar_id].get('busy', [])
        logger.info(f"Busy times: {busy_times}")

        if busy_times:
            next_available = end_time
            for _ in range(5):
                new_end = next_available + timedelta(hours=1)
                new_query = {
                    "timeMin": next_available.isoformat() + 'Z',
                    "timeMax": new_end.isoformat() + 'Z',
                    "timeZone": 'Asia/Kathmandu',
                    "items": [{"id": calendar_id}]
                }
                result = service.freebusy().query(body=new_query).execute()
                if not result['calendars'][calendar_id].get('busy', []):
                    message = f"That time is already booked. How about {next_available.strftime('%I:%M %p')} on {next_available.strftime('%Y-%m-%d')}?"
                    return translate_text(message, language)
                next_available += timedelta(hours=1)
            message = "Sorry, no available slots in the next few hours."
            return translate_text(message, language)

        event = {
            'summary': translate_text(f"{summary} for {user.username}", language),
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
        booking = Booking.objects.create(
            user=user,
            appointment_time=start_time,
            status='PENDING'
        )
        logger.info(f"Created booking: {booking}")
        message = f"Your appointment is booked at {start_time.strftime('%I:%M %p')} on {start_time.strftime('%Y-%m-%d')}. Please come on time."
        return translate_text(message, language)
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        error_message = f"Error booking appointment: {str(e)}"
        return translate_text(error_message, language)

def get_bot_response(user_input, request):
    logger.info(f"get_bot_response: User: {request.user}, Authenticated: {request.user.is_authenticated}, Input: {user_input}")
    try:
        language = detect(user_input)
        logger.info(f"Detected language: {language}")
    except Exception as e:
        logger.warning(f"Language detection failed: {str(e)}. Defaulting to English.")
        language = 'en'

    services_text = get_all_services_text(language)
    faqs = FAQ.objects.all()
    faqs_text = "\n".join([f"Q: {faq.question}\nA: {faq.answer}" for faq in faqs])

    system_prompt = SystemMessage(content=translate_text(f"""
You are a helpful barbershop assistant. Respond in the user's language and only answer questions about:
- Haircuts
- Beard trims
- Grooming
- Appointments
- Shop hours, etc. 

Here are the current services and prices:\n{services_text}

Here are the FAQs to assist with common questions:\n{faqs_text}

If asked anything unrelated, reply with:
"I'm here to assist with barbershop-related questions only. How can I help with your grooming needs?"
""", language))

    chat = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
    messages = [
        system_prompt,
        HumanMessage(content=user_input)
    ]
    appointment_time = extract_time_from_input(user_input, language)
    if appointment_time:
        booking_response = book_appointment_on_calendar("Barbershop Appointment", appointment_time, request.user, language)
        return booking_response
    else:
        error_message = "Sorry, I couldn't understand the time for your appointment. Please specify the time clearly, e.g., '3 PM' or '15:00'."
        translated_error = translate_text(error_message, language)
        try:
            response = chat.invoke(messages)
            return translate_text(response.content, language)
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return translated_error