from django.contrib import admin
from .models import Channel, Schedule, RecurringSchedule, TimeShiftProfile


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "enabled",
        "input_type",
        "input_url",
        "output_type",
        "output_target",
        "video_mode",
        "audio_mode",
        "created_at",
    )
    list_filter = (
        "enabled",
        "input_type",
        "output_type",
        "video_mode",
        "audio_mode",
        "hardware_preference",
    )
    search_fields = ("name", "input_url", "output_target")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("General", {
            "fields": ("name", "enabled"),
        }),
        ("Input", {
            "fields": (
                "input_type",
                "input_url",
                "multicast_interface",
            ),
        }),
        ("Output", {
            "fields": (
                "output_type",
                "output_target",
            ),
        }),
        ("Recording", {
            "fields": (
                "record_enabled",
                "recording_path_template",
                "recording_segment_minutes",
            ),
        }),
        ("Processing", {
            "fields": (
                "video_mode",
                "audio_mode",
                "video_codec",
                "audio_codec",
                ("target_width", "target_height", "video_bitrate"),
            ),
        }),
        ("Hardware preference", {
            "fields": ("hardware_preference",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )



@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "channel",
        "purpose",
        "enabled",
        "start_at",
        "end_at",
        "created_at",
    )
    list_filter = ("enabled", "purpose", "channel")
    search_fields = ("name",)
    autocomplete_fields = ("channel",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("General", {
            "fields": ("name", "channel", "purpose", "enabled"),
        }),
        ("Timing", {
            "fields": ("start_at", "end_at"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )



@admin.register(RecurringSchedule)
class RecurringScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "channel",
        "purpose",
        "enabled",
        "weekdays_text",  # Sat→Fri summary on one line
        "start_time",
        "end_time",
        "date_from",
        "date_to",
        "created_at",
    )
    list_filter = (
        "enabled",
        "purpose",
        "channel",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    search_fields = ("name",)
    autocomplete_fields = ("channel",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": (
                "name",
                "channel",
                "purpose",
                "enabled",
            )
        }),
        ("Days of week", {
            "fields": (
                # order: Sat → Sun → Mon → Fri
                ("saturday", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday"),
            ),
            "description": "Select which days this schedule is active (Sat → Fri).",
        }),
        ("Time window", {
            "fields": ("start_time", "end_time", "date_from", "date_to"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )


@admin.register(TimeShiftProfile)
class TimeShiftProfileAdmin(admin.ModelAdmin):
    list_display = (
        "channel",
        "enabled",
        "delay_minutes",
        "output_udp_url",
        "created_at",
    )
    list_filter = ("enabled",)
    autocomplete_fields = ("channel",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("channel", "enabled"),
        }),
        ("Delay settings", {
            "fields": ("delay_minutes", "output_udp_url"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )
