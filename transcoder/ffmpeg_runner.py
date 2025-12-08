# transcoder/ffmpeg_runner.py
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import List
from django.conf import settings
from .models import Channel, VideoMode, AudioMode


@dataclass
class FFmpegJobConfig:
    channel: Channel
    purpose: str  # "live_forward" | "record" | "playback"

    def build_command(self) -> List[str]:
        """
        Builds an ffmpeg command for this channel & purpose.

        For now:
        - Copy/remux by default (no transcoding).
        - Only handles:
          - input_type: FILE or UDP_MULTICAST
          - purpose: "live_forward" with HLS output
        We’ll extend it later.
        """
        chan = self.channel
        input_url = chan.input_url
        output_target = chan.output_target

        # Base ffmpeg command
        args: List[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]

        # Multicast helper (we’ll refine later)
        if chan.input_type == "udp_multicast":
            if "fifo_size=" not in input_url:
                sep = "&" if "?" in input_url else "?"
                input_url = f"{input_url}{sep}fifo_size=1000000&overrun_nonfatal=1"

        # Input
        args += ["-i", input_url]

        # Video: copy by default
        if chan.video_mode == VideoMode.COPY:
            args += ["-c:v", "copy"]
        else:
            # We’ll plug transcoding & GPU logic here later
            args += ["-c:v", "libx264"]

        # Audio: copy / disable / transcode
        if chan.audio_mode == AudioMode.COPY:
            args += ["-c:a", "copy"]
        elif chan.audio_mode == AudioMode.DISABLE:
            args += ["-an"]
        else:
            # Basic default for now
            args += ["-c:a", chan.audio_codec or "aac"]

        # Purpose-specific handling
        if self.purpose == "live_forward":
            # Same as before: forward live to an output
            if chan.output_type == "hls":
                out_dir = Path(output_target)
                out_dir.mkdir(parents=True, exist_ok=True)
                playlist_path = out_dir / "index.m3u8"

                args += [
                    "-f", "hls",
                    "-hls_time", "4",
                    "-hls_list_size", "10",
                    "-hls_flags", "delete_segments",
                    str(playlist_path),
                ]

            elif chan.output_type == "rtmp":
                args += ["-f", "flv", output_target]

            elif chan.output_type == "udp_ts":
                args += ["-f", "mpegts", output_target]

            else:
                # fallback: TS file
                args += ["-f", "mpegts", output_target]

        elif self.purpose == "record":
            # Record to disk in segments, using recording_path_template
            # For now we create a simple folder based on channel name + date.
            from datetime import datetime

            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            # You can expand template usage later
            base_dir_str = chan.recording_path_template.format(
                channel=chan.name,
                date=date_str,
                time=now.strftime("%H%M%S"),
            )
            base_dir = Path(base_dir_str)

            # If not absolute, make it relative to MEDIA_ROOT
            if not base_dir.is_absolute():
                base_dir = Path(settings.MEDIA_ROOT) / base_dir

            base_dir.mkdir(parents=True, exist_ok=True)

            # Example filename pattern: channel_00001.ts, channel_00002.ts, ...
            segment_pattern = str(base_dir / f"{chan.name}_%05d.ts")

            segment_seconds = chan.recording_segment_minutes * 60

            args += [
                "-f", "segment",
                "-segment_time", str(segment_seconds),
                "-reset_timestamps", "1",
                segment_pattern,
            ]

        # We’ll add "playback" cases later (for time-shift).
        return args


def build_ffmpeg_cmd_for_channel(channel_id: int, purpose: str = "live_forward") -> str:
    """
    Helper: loads the Channel and returns a shell-safe ffmpeg command string.
    """
    chan = Channel.objects.get(pk=channel_id)
    job = FFmpegJobConfig(channel=chan, purpose=purpose)
    cmd_list = job.build_command()
    return " ".join(shlex.quote(part) for part in cmd_list)
