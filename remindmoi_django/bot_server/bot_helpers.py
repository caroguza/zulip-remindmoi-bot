import re
import urllib.parse
from typing import Any, Dict
from datetime import timedelta, datetime

from .constants import (
    UNITS,
    SINGULAR_UNITS,
    BASE_TEMPLATE_URL,
    STREAM_TYPES,
    PUBLIC_STREAM_TYPE,
)


def get_url_params(message):
    display_recipient = message.get("display_recipient")
    stream_name = display_recipient if isinstance(display_recipient, str) else None
    recipients = []
    if isinstance(display_recipient, list):
        for recipient in reversed(display_recipient):
            recipients.append(recipient.get("email"))
    return {
        "message_type": message.get("type"),
        "stream_id": message.get("stream_id"),
        "stream_name": stream_name,
        "subject": message.get("subject"),
        "recipients": recipients,
        "message_id": message.get("id")
    }


def create_conversation_url(
    message_type, stream_id, stream_name, subject, recipients, message_id
):
    current_url = f"{STREAM_TYPES[message_type]}"
    if message_type == PUBLIC_STREAM_TYPE:
        assert subject
        stream_full_id = f"{stream_id}-{stream_name}"
        current_url = f"{current_url}/{stream_full_id}/subject/{subject}"
    else:
        assert not subject
        involved = ",".join(recipients)
        current_url = f"{current_url}/{involved}"
    current_url = f"{current_url}/near/{message_id}"
    safe_url = urllib.parse.quote(current_url)
    url = f"{BASE_TEMPLATE_URL}/{safe_url}"
    return url


def is_add_command(content: str, units=UNITS + SINGULAR_UNITS) -> bool:
    """
    Ensure message is in form <COMMAND> reminder <int> UNIT <str>
    """
    try:
        command = content.split(" ", maxsplit=4)  # Ensure the last element is str
        assert command[0] == "add"
        assert type(int(command[1])) == int
        assert command[2] in units
        assert type(command[3]) == str
        return True
    except (IndexError, AssertionError, ValueError):
        return False


def is_remove_command(content: str) -> bool:
    try:
        command = content.split(" ")
        assert command[0] == "remove"
        assert type(int(command[1])) == int
        return True
    except (AssertionError, IndexError, ValueError):
        return False


def is_list_command(content: str) -> bool:
    try:
        command = content.split(" ")
        assert command[0] == "list"
        return True
    except (AssertionError, IndexError, ValueError):
        return False


def is_repeat_reminder_command(content: str, units=UNITS + SINGULAR_UNITS) -> bool:
    try:
        command = content.split(" ")
        assert command[0] == "repeat"
        assert type(int(command[1])) == int
        assert command[2] == "every"
        assert type(int(command[3])) == int
        assert command[4] in units
        return True
    except (AssertionError, IndexError, ValueError):
        return False


def is_multi_remind_command(content: str) -> bool:
    try:
        command = content.split(" ", maxsplit=2)
        assert command[0] == "multiremind"
        assert type(int(command[1])) == int
        return True
    except (AssertionError, IndexError, ValueError):
        return False


def is_remindme_command(content: str) -> bool:
    try:
        result = re.match(r"me\s+\d+\s+\w+(\s+--multi\s+(@\w+)+)?", content)
        return result is not None
    except (AssertionError, IndexError, ValueError):
        return False


def has_multi(content: str) -> bool:
    return "--multi" in content


def parse_remindme_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    url_params = get_url_params(message)
    url = create_conversation_url(**url_params)
    content = message["content"].split(
        " ", maxsplit=3
    )
    return {
        "zulip_user_email": message["sender_email"],
        "title": url,
        "created": message["timestamp"],
        "deadline": compute_deadline_timestamp(
            message["timestamp"], content[1], content[2]
        ),
        "active": True,
    }


def parse_add_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    content = message["content"].split(
        " ", maxsplit=3
    )  # Ensure the last element is str
    return {
        "zulip_user_email": message["sender_email"],
        "title": content[3],
        "created": message["timestamp"],
        "deadline": compute_deadline_timestamp(
            message["timestamp"], content[1], content[2]
        ),
        "active": True,
    }


def parse_remove_command_content(content: str) -> Dict[str, Any]:
    command = content.split(" ")
    return {"reminder_id": command[1]}


def parse_repeat_command_content(content: str) -> Dict[str, Any]:
    command = content.split(" ")
    return {
        "reminder_id": command[1],
        "repeat_unit": command[4],
        "repeat_value": command[3],
    }


def parse_multi_remind_command_content(content: str) -> Dict[str, Any]:
    """
    multiremind 23 @**Jose** @**Max** ->
    {'reminder_id': 23, 'users_to_remind': ['Jose', Max]}
    """
    command = content.split(" ", maxsplit=2)
    users_to_remind = command[2].replace("*", "").replace("@", " ").strip().split(" ",)
    return {"reminder_id": command[1], "users_to_remind": users_to_remind}


def generate_reminders_list(response: Dict[str, Any]) -> str:
    bot_response = ""
    reminders_list = response["reminders_list"]
    if not reminders_list:
        return "No reminders avaliable."
    for reminder in reminders_list:
        bot_response += f"""
        \nReminder id {reminder['reminder_id']}, titled {reminder['title']}, is scheduled on {reminder['deadline']}
        """
    return bot_response


def compute_deadline_timestamp(
    timestamp_submitted: str, time_value: int, time_unit: str
) -> str:
    """
    Given a submitted stamp and an interval,
    return deadline timestamp.
    """
    import pdb; pdb.set_trace()
    if time_unit in SINGULAR_UNITS:  # Convert singular units to plural
        time_unit = f"{time_unit}s"

    interval = timedelta(**{time_unit: int(time_value)})
    datetime_submitted = datetime.fromtimestamp(timestamp_submitted)
    return (datetime_submitted + interval).timestamp()


def is_iso_time_command(message: str) -> bool:
    try:
        import pdb; pdb.set_trace()
        result = re.match(r"at\s+\b([0-9]|1[0-2])\b(:(\b(0+[0-9]|[1-4][0-9]|5[0-9])\b))?\s+(am|pm)*", message["content"])
        
        if result is not None:
            current_date = datetime.fromtimestamp(message["timestamp"])
            hour = get_time_period_hour(result.group(1), result.group())
            minutes = get_minutes(result.group(2))
            reminder_date = current_date.replace(hour=hour, minute=minutes)
            
            return reminder_date > current_date
        return False
    except (AssertionError, IndexError, ValueError):
        return False

def parse_add_is_time_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    #import pdb; pdb.set_trace()
    content = message["content"].split(" ")
    reminder_time = content[1]
    time_period = content[2]
    reminder_title = content[3] if len(content) >= 4 is not None else 'Reminder'
    current_hour = int((datetime.fromtimestamp(message["timestamp"])).hour)
    current_minute = int((datetime.fromtimestamp(message["timestamp"])).minute)
    reminder_hour = get_time_period_hour(reminder_time, time_period)
    reminder_minutes = get_minutes(reminder_time)

    total_time = (reminder_hour - current_hour) * 60 + (reminder_minutes - current_minute)

    return {
        "zulip_user_email": message["sender_email"],
        "title": reminder_title,
        "created": message["timestamp"],
        "deadline": compute_deadline_timestamp(message["timestamp"], total_time, 'minutes'),
        "active": True,
    }

def get_time_period_hour(string_hour, period):
    if 'pm' in (period):
        return 12 + int(string_hour.split(":")[0]) if ':' in string_hour else 12 + int(string_hour)
    return int(string_hour)

def get_minutes(string_time):
    if string_time is not None and ':' in string_time:
        return int(string_time.split(":")[1])
    return 0
