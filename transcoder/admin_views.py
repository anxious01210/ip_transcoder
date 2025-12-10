# transcoder/admin_views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from .models import Channel, RecurringSchedule, TimeShiftProfile, JobPurpose


@staff_member_required
def transcoder_overview(request):
    """
    High-level overview of channels, timeshift profiles, and schedules.
    Visible only to staff via /admin/transcoder/overview/.
    """
    # Channels with their 1:1 TimeShiftProfile
    channels = (
        Channel.objects.all()
        .select_related("timeshift_profile")
        .order_by("id")
    )

    # All recurring schedules, grouped by channel + purpose
    schedules_by_channel = {}
    for ch in channels:
        schedules_by_channel[ch.id] = {
            "record": [],
            "playback": [],
            "other": [],
        }

    for rs in RecurringSchedule.objects.select_related("channel").order_by("channel_id", "id"):
        if rs.channel_id not in schedules_by_channel:
            # In case there is a schedule for a channel not in the queryset
            schedules_by_channel[rs.channel_id] = {
                "record": [],
                "playback": [],
                "other": [],
            }

        if rs.purpose == JobPurpose.RECORD:
            bucket = "record"
        elif rs.purpose == JobPurpose.PLAYBACK:
            bucket = "playback"
        else:
            bucket = "other"

        schedules_by_channel[rs.channel_id][bucket].append(rs)

    context = {
        "title": "IP Transcoder Overview",
        "channels": channels,
        "schedules_by_channel": schedules_by_channel,
    }
    return render(request, "admin/transcoder/overview.html", context)
