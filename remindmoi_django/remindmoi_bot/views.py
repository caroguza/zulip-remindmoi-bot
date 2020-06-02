import os
import json

import caldav
import pytz
from datetime import datetime, timedelta

import vobject
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from remindmoi_bot.auth import OAuth, set_oauth_credentials
from remindmoi_bot.models import Reminder, OAuthUser, HistoryEvents
from remindmoi_bot.scheduler import scheduler
from remindmoi_bot.zulip_utils import (
    send_private_zulip_reminder,
    repeat_unit_to_interval,
    get_user_emails,
    convert_date_to_iso,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICLOUD_SECRETS = os.path.join(BASE_DIR, "client_secret.json")


@csrf_exempt
@require_POST
def add_reminder(request):
    # TODO: make it safer. Add CSRF validation. Sanitize/validate post data
    reminder_obj = json.loads(request.body)  # Create and save remninder object
    zulip_emails = reminder_obj.get("zulip_user_email")
    if reminder_obj.get("is_multi"):
        zulip_usernames = reminder_obj.get("zulip_usernames")
        zulip_emails = get_user_emails(zulip_usernames) + [zulip_emails]
        zulip_emails = ",".join([email for email in zulip_emails])
    reminder = Reminder.objects.create(
        zulip_user_email=zulip_emails,
        title=reminder_obj["title"],
        created=datetime.utcfromtimestamp(reminder_obj["created"]).replace(
            tzinfo=pytz.utc
        ),
        deadline=datetime.utcfromtimestamp(reminder_obj["deadline"]).replace(
            tzinfo=pytz.utc
        ),
    )
    reminder.save()
    scheduler.add_job(  # Schedule reminder
        send_private_zulip_reminder,
        "date",
        run_date=reminder.deadline,
        args=[reminder.reminder_id],
        # Create job name from title and reminder id
        id=(str(reminder.reminder_id) + reminder.title),
    )
    return JsonResponse({"success": True, "reminder_id": reminder.reminder_id})


def isoadd_reminder(request):
    reminder_obj = json.loads(request.body)  # Create and save remninder object
    reminder = Reminder.objects.create(
        zulip_user_email=reminder_obj["zulip_user_email"],
        title=reminder_obj["title"],
        created=datetime.utcfromtimestamp(reminder_obj["created"]).replace(
            tzinfo=pytz.utc
        ),
        deadline=datetime.utcfromtimestamp(reminder_obj["deadline"]).replace(
            tzinfo=pytz.utc
        ),
    )
    reminder.save()
    scheduler.add_job(  # Schedule reminder
        send_private_zulip_reminder,
        "date",
        run_date=reminder.deadline,
        args=[reminder.reminder_id],
        # Create job name from title and reminder id
        id=(str(reminder.reminder_id) + reminder.title),
    )
    return JsonResponse({"success": True, "reminder_id": reminder.reminder_id})


@csrf_exempt
@require_POST
def multi_remind(request):
    """
    Get reminder object and modify the zulip_sender email to
    add emails of other users, comma seperated.
    """
    multi_remind_request = json.loads(request.body)
    reminder_id = multi_remind_request["reminder_id"]
    usernames = multi_remind_request["users_to_remind"]
    try:
        reminder = Reminder.objects.get(reminder_id=int(reminder_id))
    except Reminder.DoesNotExist:
        return JsonResponse({"success": False, "reminder_id": reminder_id})
    user_emails_to_remind = get_user_emails(usernames) + [reminder.zulip_user_email]
    reminder.zulip_user_email = ",".join(user_emails_to_remind)
    reminder.save()

    return JsonResponse(
        {
            "success": True,
            "reminder_id": reminder.reminder_id,
            "user_emails_to_remind": usernames,
        }
    )


@csrf_exempt
@require_POST
def remove_reminder(request):
    reminder_id = json.loads(request.body)["reminder_id"]
    reminder = Reminder.objects.get(reminder_id=int(reminder_id))
    scheduler.remove_job(
        (str(reminder.reminder_id) + reminder.title)
    )  # Remove reminder job
    reminder.delete()  # Remove reminder object
    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def list_reminders(request):
    response_reminders = []  # List of reminders to be returned to the client

    zulip_user_email = json.loads(request.body)["zulip_user_email"]
    user_reminders = Reminder.objects.filter(
        zulip_user_email__icontains=zulip_user_email
    )
    # Return title and deadline (in unix timestamp) of reminders
    for reminder in user_reminders.values():
        response_reminders.append(
            {
                "title": reminder["title"],
                "deadline": convert_date_to_iso(reminder["deadline"]),
                "reminder_id": reminder["reminder_id"],
            }
        )

    return JsonResponse({"success": True, "reminders_list": response_reminders})


@csrf_exempt
@require_POST
def repeat_reminder(request):
    repeat_request = json.loads(request.body)
    reminder_id = repeat_request["reminder_id"]
    repeat_unit = repeat_request["repeat_unit"]
    repeat_value = repeat_request["repeat_value"]
    reminder = Reminder.objects.get(reminder_id=reminder_id)
    job_id = str(reminder.reminder_id) + reminder.title

    scheduler.add_job(
        send_private_zulip_reminder,
        "interval",
        **repeat_unit_to_interval(repeat_unit, repeat_value),
        args=[reminder.reminder_id],
        id=job_id
    )
    return JsonResponse({"success": True})


@csrf_exempt
@require_POST
def create_calendar_event(request):
    obj = json.loads(json.loads(request.body))

    icloud_secrets = ICLOUD_SECRETS
    with open(icloud_secrets) as secret_file:
        data = json.load(secret_file)
        secrets_dict = {key: value for key, value in data["web"].items()}

    oaut_user_qs = OAuthUser.objects.filter(zulip_user_email=obj['email'])

    if not oaut_user_qs.exists():
        return JsonResponse({"failure": "the user doesn't exist"}, status=404)

    oaut_user = oaut_user_qs.first()

    credentials = set_oauth_credentials(
        secrets_dict=secrets_dict,
        access_token=oaut_user.access_token,
        token_expiry=oaut_user.token_expiry,
        refresh_token=oaut_user.refresh_token,
    )

    auth = OAuth(credentials)
    caldav_client = caldav.DAVClient(
        "https://cloud.monadical.com/remote.php/dav",
        auth=auth)

    principal = caldav_client.principal()
    calendars = principal.calendars()
    personal_calendar = None
    for calendar in calendars:
        if calendar.name == "Personal":
            personal_calendar = calendar

    assert personal_calendar is not None

    # created the VCalendar
    cal = vobject.iCalendar()
    cal.add('prodid').value = "-//Example Corp.//CalDAV Client//EN"
    cal.add('vevent')
    first_ev = cal.vevent

    # add body to first vevent
    start = cal.vevent.add('dtstart')
    str_datetime_start = f"{obj['event_date']} {obj['event_time']}"
    datetime_start = datetime.strptime(str_datetime_start, "%d-%m-%Y %H:%M")
    timezone = pytz.timezone("utc")
    datetime_start = timezone.localize(datetime_start)
    start.value = datetime_start
    end = cal.vevent.add('dtend')
    datetime_end = datetime_start + timedelta(minutes=30)
    end.value = datetime_end
    first_ev.add('summary').value = obj["title"]

    history = HistoryEvents.objects.create(
        zulip_user_email=obj['email'],
        dt_start=datetime_start,
    )

    first_ev.add('uid').value = f"{history.id}-zulip-bot"

    # fill the whole data required what are missing to create the event
    icalstream = cal.serialize()

    # add event to calendar
    personal_calendar.add_event(icalstream)

    return JsonResponse({"success": True}, status=200)
