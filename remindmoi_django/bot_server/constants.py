UNITS = ["minutes", "hours", "days", "weeks"]
SINGULAR_UNITS = ["minute", "hour", "day", "week"]
REPEAT_UNITS = ["weekly", "daily", "monthly"] + ["minutely"]  # Remove after testing

ENDPOINT_URL = "http://localhost:8000"
ADD_ENDPOINT = ENDPOINT_URL + "/add_reminder"
REMOVE_ENDPOINT = ENDPOINT_URL + "/remove_reminder"
LIST_ENDPOINT = ENDPOINT_URL + "/list_reminders"
REPEAT_ENDPOINT = ENDPOINT_URL + "/repeat_reminder"
MULTI_REMIND_ENDPOINT = ENDPOINT_URL + "/multi_remind"
CALENDAR_REMIND_ENDPOINT = ENDPOINT_URL + "/create-calendar-event"
AUTHORIZED_USER = ENDPOINT_URL + "/email-authorized"
REFRESH_TOKEN = ENDPOINT_URL + "/auth/nextcloud/refresh-token"

BASE_URL = "https://zulip.monadical.com"
BASE_TEMPLATE_URL = f"{BASE_URL}/#narrow"

PUBLIC_STREAM_TYPE = "stream"
STREAM_TYPES = {PUBLIC_STREAM_TYPE: PUBLIC_STREAM_TYPE, "private": "pm-with"}
