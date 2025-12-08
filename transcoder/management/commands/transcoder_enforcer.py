import subprocess
import time
from typing import Dict, Tuple

from django.core.management.base import BaseCommand
from django.utils import timezone

from transcoder.ffmpeg_runner import FFmpegJobConfig
from transcoder.models import Schedule, RecurringSchedule

JobKey = Tuple[str, int]  # ("oneoff" or "recurring", schedule_id)


class Command(BaseCommand):
    help = "Enforcer: starts/stops ffmpeg jobs based on one-off and recurring schedules."

    POLL_INTERVAL = 5  # seconds

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting transcoder enforcer..."))

        # job_key -> subprocess.Popen
        running: Dict[JobKey, subprocess.Popen] = {}

        try:
            while True:
                now = timezone.localtime()

                # ============================
                # 1) Collect ACTIVE one-off schedules
                # ============================
                active_oneoff = list(
                    Schedule.objects.filter(
                        enabled=True,
                        start_at__lte=now,
                        end_at__gt=now,
                    ).select_related("channel")
                )

                # Build a list of desired jobs
                desired_jobs: Dict[JobKey, Tuple[str, str, str]] = {}
                # value = (channel_name, purpose, schedule_name)

                for sched in active_oneoff:
                    key: JobKey = ("oneoff", sched.id)
                    desired_jobs[key] = (
                        sched.channel.name,
                        sched.purpose,
                        sched.name,
                    )

                # ============================
                # 2) Collect ACTIVE recurring schedules
                # ============================
                active_recurring = list(
                    RecurringSchedule.objects.filter(
                        enabled=True,
                    ).select_related("channel")
                )

                for rs in active_recurring:
                    if not rs.is_active_now(now):
                        continue

                    key: JobKey = ("recurring", rs.id)
                    desired_jobs[key] = (
                        rs.channel.name,
                        rs.purpose,
                        rs.name,
                    )

                desired_keys = set(desired_jobs.keys())

                # ============================
                # 3) Start jobs that should be running but are not
                # ============================
                for key in desired_keys:
                    if key in running:
                        continue  # already running

                    kind, ident = key

                    if kind == "oneoff":
                        sched = next(s for s in active_oneoff if s.id == ident)
                        chan = sched.channel
                        purpose = sched.purpose
                        name = sched.name
                    else:
                        rs = next(s for s in active_recurring if s.id == ident)
                        chan = rs.channel
                        purpose = rs.purpose
                        name = rs.name

                    self.stdout.write(
                        self.style.WARNING(
                            f"Starting job: {kind}={ident} name={name!r} "
                            f"channel={chan.name!r} purpose={purpose}"
                        )
                    )

                    job = FFmpegJobConfig(channel=chan, purpose=purpose)
                    cmd_list = job.build_command()
                    proc = subprocess.Popen(cmd_list)
                    running[key] = proc

                # ============================
                # 4) Stop jobs that should no longer be running
                # ============================
                for key, proc in list(running.items()):
                    if key not in desired_keys:
                        kind, ident = key
                        self.stdout.write(
                            self.style.WARNING(
                                f"Stopping job for {kind}={ident} (no longer active)..."
                            )
                        )
                        if proc.poll() is None:
                            proc.terminate()
                        running.pop(key, None)

                # ============================
                # 5) Cleanup finished processes
                # ============================
                for key, proc in list(running.items()):
                    if proc.poll() is not None:
                        kind, ident = key
                        self.stdout.write(
                            self.style.WARNING(
                                f"Job for {kind}={ident} exited (return code {proc.returncode})"
                            )
                        )
                        running.pop(key, None)

                time.sleep(self.POLL_INTERVAL)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Enforcer stopping (Ctrl+C)..."))
            for key, proc in running.items():
                if proc.poll() is None:
                    kind, ident = key
                    self.stdout.write(
                        self.style.WARNING(
                            f"Terminating ffmpeg for {kind}={ident}..."
                        )
                    )
                    proc.terminate()
            self.stdout.write(self.style.SUCCESS("Enforcer stopped."))
