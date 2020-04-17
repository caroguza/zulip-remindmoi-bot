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
        "message_id": message.get("id"),
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
        result = re.match(r"multi\s+\d+(((@\w+)(\s)?)+)?", content)

        return result is not None
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


def is_iso_time_command(message: str) -> bool:
    try:
        result = re.match(
            r"me at\s+\b([0-9]|1[0-2])\b(:\b(0+[0-9]|[1-4][0-9]|5[0-9])\b)?\s+(am|pm)*(\s+--multi\s+(@\w+)+)?",
            message["content"],
            flags=re.IGNORECASE,
        )

        if result is not None:
            current_time = datetime.fromtimestamp(message["timestamp"]).time()
            hour = int(result.group(1))
            period = result.group(4).lower()
            reminder_hour = hour if "am" == period else 12 + hour
            minutes = int(result.group(3)) if result.group(3) is not None else 0
            reminder_time = current_time.replace(hour=reminder_hour, minute=minutes)

            return reminder_time > current_time
        return False
    except (AssertionError, IndexError, ValueError):
        return False


def is_iso_date_command(message: str) -> bool:
    try:
        result = re.match(
            r"me\s+at\s+\b(\b(20[2-8][0-9]|209[0-9]|2[1-9][0-9]{2}|[3-9][0-9]{3})\b-\b(0+[1-9]|1[0-2])\b-\b(0+[1-9]|[12][0-9]|3[01])\b)\b\s+\b(\b(0+[0-9]|1[0-9]|2[0-3])\b:\b(0+[0-9]|[1-4][0-9]|5[0-9])\b)(\s+--multi\s+(@\w+)+)?",
            message["content"],
        )
        if result is not None:
            remainder_datetime = f"{result.group(1)} {result.group(5)}"
            new_datetime = datetime.strptime(remainder_datetime, "%Y-%m-%d %H:%M")
            current_datetime = datetime.fromtimestamp(message["timestamp"])
            return new_datetime > current_datetime
        return False
    except (AssertionError, IndexError, ValueError):
        return False


def parse_remindme_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    url_params = get_url_params(message)
    url = create_conversation_url(**url_params)
    content = message["content"].split(" ", maxsplit=4)
    zulip_usernames = []
    is_multi = has_multi(message["content"])
    if is_multi:
        zulip_usernames = (
            content[4].replace("*", "").replace("@", " ").strip().split(" ",)
        )
    return {
        "zulip_user_email": message["sender_email"],
        "zulip_usernames": zulip_usernames,
        "title": url,
        "created": message["timestamp"],
        "deadline": compute_deadline_timestamp(
            message["timestamp"], content[1], content[2]
        ),
        "is_multi": is_multi,
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


def parse_add_is_time_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    url_params = get_url_params(message)
    url = create_conversation_url(**url_params)

    content = message["content"].split(" ")
    zulip_usernames = []
    is_multi = has_multi(message["content"])
    if is_multi:
        zulip_usernames = (
            content[5].replace("*", "").replace("@", " ").strip().split(" ",)
        )

    current_time = datetime.fromtimestamp(message["timestamp"])
    time_period = content[3]
    reminder_time_splitted = content[2].split(":")
    reminder_splitted_hour = int(reminder_time_splitted[0])
    reminder_hour = (
        reminder_splitted_hour if time_period == "am" else 12 + reminder_splitted_hour
    )
    try:
        reminder_minutes = int(reminder_time_splitted[1])
    except IndexError:
        reminder_minutes = 0

    total_time = (reminder_hour - current_time.hour) * 60 + (
        reminder_minutes - current_time.minute
    )

    return {
        "zulip_user_email": message["sender_email"],
        "zulip_usernames": zulip_usernames,
        "title": url,
        "created": message["timestamp"],
        "deadline": compute_deadline_timestamp(
            message["timestamp"], total_time, "minutes"
        ),
        "is_multi": is_multi,
        "active": True,
    }


def parse_add_date_command_content(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Given a message object with reminder details,
    construct a JSON/dict.
    """
    url_params = get_url_params(message)
    url = create_conversation_url(**url_params)

    content = message["content"].split(" ")

    zulip_usernames = []
    is_multi = has_multi(message["content"])
    if is_multi:
        zulip_usernames = (
            content[5].replace("*", "").replace("@", " ").strip().split(" ",)
        )

    reminder_datetime = f"{content[2]} {content[3]}"
    deadline = datetime.strptime(reminder_datetime, "%Y-%m-%d %H:%M").timestamp()
    return {
        "zulip_user_email": message["sender_email"],
        "zulip_usernames": zulip_usernames,
        "title": url,
        "created": message["timestamp"],
        "deadline": deadline,
        "is_multi": is_multi,
        "active": True,
    }


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

    if time_unit in SINGULAR_UNITS:  # Convert singular units to plural
        time_unit = f"{time_unit}s"

    interval = timedelta(**{time_unit: int(time_value)})
    datetime_submitted = datetime.fromtimestamp(timestamp_submitted)
    return (datetime_submitted + interval).timestamp()
