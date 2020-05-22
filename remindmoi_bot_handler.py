import json
import requests

from datetime import datetime
from dateutil.tz import gettz

from typing import Any, Dict

from remindmoi_django.bot_server.constants import (
    ADD_ENDPOINT,
    REMOVE_ENDPOINT,
    LIST_ENDPOINT,
    REPEAT_ENDPOINT,
    MULTI_REMIND_ENDPOINT,
    CALENDAR_REMIND_ENDPOINT, AUTHORIZED_USER, REFRESH_TOKEN)
from remindmoi_django.bot_server.bot_helpers import (
    is_add_command,
    is_remove_command,
    is_list_command,
    is_repeat_reminder_command,
    is_multi_remind_command,
    is_remindme_command,
    parse_add_command_content,
    parse_remove_command_content,
    generate_reminders_list,
    parse_repeat_command_content,
    parse_multi_remind_command_content,
    parse_remindme_command_content,
    is_iso_time_command,
    parse_add_is_time_command_content,
    is_iso_date_command,
    parse_add_date_command_content,
    is_calendar_remind_command,
    parse_calendar_remind_command_content)
from remindmoi_django.bot_server.constants import ENDPOINT_URL

USAGE = """
A bot that schedules reminders for users.

To store a reminder, mention or send a message to the bot in the following format:

`add int <UNIT> <title_of_reminder>`

`add 1 day clean the dishes`
`add 10 hours eat`

Avaliable time units: minutes, hours, days, weeks

To remove a reminder:
`remove <reminder_id>`

To list reminders:
`list`

To repeat a reminder: 
repeat <reminder_id> every <int> <time_unit>

`repeat 23 every 2 weeks`

Avaliable units: days, weeks, months

"""

REDIRECT_LOGIN_URL = "cloud-login/"


class RemindMoiHandler(object):
    """
    A docstring documenting this bot.
    the reminder bot reminds people of its reminders
    """

    def usage(self) -> str:
        return USAGE

    def handle_message(self, message: Dict[str, Any], bot_handler: Any) -> None:
        bot_response = get_bot_response(message, bot_handler)
        bot_handler.send_reply(message, bot_response)


def get_bot_response(message: Dict[str, Any], bot_handler: Any) -> str:
    message_content = message["content"]
    if message_content.startswith(("help", "?", "halp")):
        return USAGE

    try:
        if is_iso_date_command(message_content, message["timestamp"]):
            reminder_object = parse_add_date_command_content(message)
            response = requests.post(url=ADD_ENDPOINT, json=reminder_object)
            response = response.json()
            assert response["success"]
            message = f"Reminder stored. title: {reminder_object['title']} Your reminder id is: {response['reminder_id']}. "
            return message
        if is_iso_time_command(message_content, message["timestamp"]):
            reminder_object = parse_add_is_time_command_content(message)
            response = requests.post(url=ADD_ENDPOINT, json=reminder_object)
            response = response.json()
            assert response["success"]
            return f"Reminder stored. Your reminder id is: {response['reminder_id']}. title: {reminder_object['title']}"
        if is_remindme_command(message_content):
            reminder_object = parse_remindme_command_content(message)
            response = requests.post(url=ADD_ENDPOINT, json=reminder_object)
            response = response.json()
            assert response["success"]
            return f"Reminder stored. Your reminder id is: {response['reminder_id']}. url: {reminder_object['title']}"
        if is_add_command(message_content):
            reminder_object = parse_add_command_content(message)
            response = requests.post(url=ADD_ENDPOINT, json=reminder_object)
            response = response.json()
            assert response["success"]
            return f"Reminder stored. Your reminder id is: {response['reminder_id']}"
        if is_remove_command(message_content):
            reminder_id = parse_remove_command_content(message_content)
            response = requests.post(url=REMOVE_ENDPOINT, json=reminder_id)
            response = response.json()
            assert response["success"]
            return "Reminder deleted."
        if is_list_command(message_content):
            zulip_user_email = {"zulip_user_email": message["sender_email"]}
            response = requests.post(url=LIST_ENDPOINT, json=zulip_user_email)
            response = response.json()
            assert response["success"]
            return generate_reminders_list(response)
        if is_repeat_reminder_command(message_content):
            repeat_request = parse_repeat_command_content(message_content)
            response = requests.post(url=REPEAT_ENDPOINT, json=repeat_request)
            response = response.json()
            assert response["success"]
            return f"Reminder will be repeated every {repeat_request['repeat_value']} {repeat_request['repeat_unit']}."
        if is_multi_remind_command(message_content):
            multi_remind_request = parse_multi_remind_command_content(message_content)
            response = requests.post(
                url=MULTI_REMIND_ENDPOINT, json=multi_remind_request
            )
            response = response.json()
            assert response["success"]
            emails = ", ".join(
                [f"@**{email}**" for email in response["user_emails_to_remind"]]
            )
            return f"Reminder will be sent to {emails}. Your reminder id is: {response['reminder_id']}."
        if is_calendar_remind_command(message_content):
            user_email = message["sender_email"]
            exists_response = requests.get(
                url=AUTHORIZED_USER,
                params={"email": user_email},
            )
            if exists_response.status_code == 404:
                authorize_url = f"{ENDPOINT_URL}/{REDIRECT_LOGIN_URL}"
                return f"please go to {authorize_url} to authorize the zulip bot to add a event in your calendar"

            json_exists_response = exists_response.json()
            if json_exists_response["user_expired"]:
                requests.get(
                    url=REFRESH_TOKEN,
                    params={"email": user_email},
                )
            calendar_remind_request = parse_calendar_remind_command_content(message)
            try:
                response = requests.post(
                    url=CALENDAR_REMIND_ENDPOINT,
                    json=json.dumps(calendar_remind_request),
                )
            except Exception as e:
                print(e)
                return f"The event wasn't add to the calendar"
            return f"Reminder will be scheduled to {calendar_remind_request['email']} at {calendar_remind_request['event_date']} {calendar_remind_request['event_time']}. "
        return "Invalid input. Please check help."
    except requests.exceptions.ConnectionError:
        return "Server not running, call Karim"
    except (json.JSONDecodeError, AssertionError):
        return "Something went wrong"
    except OverflowError:
        return "What's wrong with you?"


handler_class = RemindMoiHandler
