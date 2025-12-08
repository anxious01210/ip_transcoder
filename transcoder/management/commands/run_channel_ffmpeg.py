import subprocess
from django.core.management.base import BaseCommand, CommandError

from transcoder.ffmpeg_runner import FFmpegJobConfig
from transcoder.models import Channel


class Command(BaseCommand):
    help = "Run ffmpeg for a given Channel (blocking test mode)."

    def add_arguments(self, parser):
        parser.add_argument("channel_id", type=int, help="ID of the Channel")
        parser.add_argument(
            "--purpose",
            choices=["live_forward", "record"],
            default="live_forward",
            help="Which job type to run",
        )

    def handle(self, *args, **options):
        channel_id = options["channel_id"]
        purpose = options["purpose"]

        try:
            chan = Channel.objects.get(pk=channel_id)
        except Channel.DoesNotExist:
            raise CommandError(f"Channel with id={channel_id} does not exist.")

        job = FFmpegJobConfig(channel=chan, purpose=purpose)
        cmd_list = job.build_command()

        self.stdout.write(self.style.WARNING("Running FFmpeg:"))
        self.stdout.write(" ".join(cmd_list))

        proc = subprocess.Popen(cmd_list)

        try:
            proc.wait()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Stopping FFmpeg..."))
            proc.terminate()
            proc.wait()

        self.stdout.write(self.style.SUCCESS("FFmpeg stopped."))
