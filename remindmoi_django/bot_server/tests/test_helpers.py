import random
import urllib.parse
import datetime

from django.test.testcases import TestCase
from .test_utils import PRIVATE_MESSAGE, PUBLIC_MESSAGE

from bot_server.constants import UNITS, SINGULAR_UNITS, BASE_TEMPLATE_URL
from bot_server.bot_helpers import (
    is_remindme_command,
    get_url_params,
    create_conversation_url,
    is_multi_remind_command,
    is_iso_time_command,
    is_iso_date_command,
)


class HelperTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.users = ["@juan", "@carolina", "@henry"]

    def test_is_remindme_command_no_multi(self):
        for unit in UNITS + SINGULAR_UNITS:
            command = f"me {random.randint(0, 100)} {unit}"
            self.assertTrue(is_remindme_command(command))

    def test_is_remindme_command_multi(self):
        for unit in UNITS + SINGULAR_UNITS:
            users_amount = random.randint(1, len(self.users))
            users = set()
            for index in range(users_amount):
                users.add(self.users[index])
            command = f"me {random.randint(0, 100)} {unit} --multi {''.join(users)}"
            self.assertTrue(is_remindme_command(command))

    def test_is_multi_remind_command(self):
        users_amount = random.randint(1, len(self.users))
        users = set()
        for index in range(users_amount):
            users.add(self.users[index])
        reminder_id = 10
        command = f"multi {reminder_id} {''.join(users)}"
        self.assertTrue(is_multi_remind_command(command))

    def test_get_url_params_private(self):
        expected_dict = {
            "message_type": PRIVATE_MESSAGE.get("type"),
            "stream_id": None,
            "stream_name": None,
            "subject": PRIVATE_MESSAGE.get("subject"),
            "recipients": [
                pm.get("email") for pm in reversed(PRIVATE_MESSAGE["display_recipient"])
            ],
            "message_id": PRIVATE_MESSAGE.get("id"),
        }

        result_dict = get_url_params(PRIVATE_MESSAGE)
        self.assertEqual(expected_dict, result_dict)

    def test_get_url_params_public(self):
        expected_dict = {
            "message_type": PUBLIC_MESSAGE.get("type"),
            "stream_id": PUBLIC_MESSAGE.get("stream_id"),
            "stream_name": PUBLIC_MESSAGE.get("display_recipient"),
            "subject": PUBLIC_MESSAGE.get("subject"),
            "recipients": [],
            "message_id": PUBLIC_MESSAGE.get("id"),
        }

        result_dict = get_url_params(PUBLIC_MESSAGE)
        self.assertEqual(expected_dict, result_dict)

    def test_create_conversation_private(self):
        expected_base_url = f"{BASE_TEMPLATE_URL}/pm-with"
        safe_emails = urllib.parse.quote(
            ",".join(
                [
                    rcp.get("email")
                    for rcp in reversed(PRIVATE_MESSAGE["display_recipient"])
                ]
            )
        )
        expected_url = (
            f"{expected_base_url}/{safe_emails}/near/{PRIVATE_MESSAGE.get('id')}"
        )
        params = get_url_params(PRIVATE_MESSAGE)
        result_url = create_conversation_url(**params)
        self.assertEqual(expected_url, result_url)

    def test_create_conversation_public(self):
        expected_base_url = f"{BASE_TEMPLATE_URL}/stream"
        expected_unsafe_url = (
            f"{PUBLIC_MESSAGE['stream_id']}-{PUBLIC_MESSAGE['display_recipient']}"
        )
        expected_unsafe_url = f"{expected_unsafe_url}/subject/{PUBLIC_MESSAGE['subject']}/near/{PUBLIC_MESSAGE['id']}"
        expected_safe_url = urllib.parse.quote(expected_unsafe_url)
        expected_url = f"{expected_base_url}/{expected_safe_url}"
        params = get_url_params(PUBLIC_MESSAGE)
        result_url = create_conversation_url(**params)
        self.assertEqual(expected_url, result_url)

    def test_is_time_command_no_minutes(self):
        current_time = datetime.datetime(9999, 12, 31, 0, 0).timestamp()
        command = f"me at {random.randint(0, 12)} am"
        self.assertTrue(is_iso_time_command(command, current_time))

    def test_is_time_command_with_minutes_multi(self):
        users_amount = random.randint(1, len(self.users))
        users = set()
        for index in range(users_amount):
            users.add(self.users[index])

        current_time = datetime.datetime(2019, 12, 31, 0, 0).timestamp()
        command = f"me at {random.randint(0, 12)}:{random.randint(0, 5)}{random.randint(0, 9)} pm  --multi {''.join(users)}"
        self.assertTrue(is_iso_time_command(command, current_time))

    def test_is_time_command_minutes_no_multi(self):
        current_time = datetime.datetime(2019, 12, 31, 0, 0).timestamp()
        command = f"me at {random.randint(0, 12)}:{random.randint(0, 5)}{random.randint(0, 9)} am"
        self.assertTrue(is_iso_time_command(command, current_time))

    def test_is_time_command(self):
        current_time = datetime.datetime(2019, 12, 31, 0, 0).timestamp()
        command = f"me at {random.randint(0, 12)} pm"
        self.assertTrue(is_iso_time_command(command, current_time))

    def test_is_date_command(self):
        current_time = datetime.datetime(2019, 12, 31, 23, 59).timestamp()
        command = "me at 2020-04-19 11:00"
        self.assertTrue(is_iso_date_command(command, current_time))

    def test_is_date_command_invalid_date(self):
        current_time = datetime.datetime(2019, 12, 31, 23, 59).timestamp()
        command = "me at 2021-02-29 11:20"
        self.assertFalse(is_iso_date_command(command, current_time))
