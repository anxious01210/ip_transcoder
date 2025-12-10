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

        Cross-platform rules:
        - FILE inputs: relative paths are resolved under MEDIA_ROOT.
        - HLS outputs: relative output_target is treated as a folder under MEDIA_ROOT.
        - Recording paths: relative recording_path_template is treated under MEDIA_ROOT.
        - Network URLs (UDP/RTSP/RTMP) are used as-is.
        """
        chan = self.channel

        raw_input_url = chan.input_url
        raw_output_target = chan.output_target

        # Base ffmpeg command – assumes "ffmpeg" is in PATH (works on Windows & Linux)
        args: List[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "warning"]

        # ------------------------
        # Input URL resolution
        # ------------------------
        input_url = raw_input_url

        if chan.input_type == "file":
            # Treat input_url as file path, relative to MEDIA_ROOT when not absolute
            in_path = Path(raw_input_url)
            if not in_path.is_absolute():
                in_path = Path(settings.MEDIA_ROOT) / in_path
            input_url = str(in_path)

        elif chan.input_type == "udp_multicast":
            # Multicast helper – keep URL as-is but ensure fifo_size & overrun flags
            if "fifo_size=" not in input_url:
                sep = "&" if "?" in input_url else "?"
                input_url = f"{input_url}{sep}fifo_size=1000000&overrun_nonfatal=1"

        # (RTSP / RTMP inputs are used as-is)

        # ------------------------
        # Input
        # ------------------------
        args += ["-i", input_url]

        # ------------------------
        # Video handling
        # ------------------------
        if chan.video_mode == VideoMode.COPY:
            args += ["-c:v", "copy"]
        else:
            # We'll plug in proper GPU/transcode logic later
            args += ["-c:v", chan.video_codec or "libx264"]

        # ------------------------
        # Audio handling
        # ------------------------
        if chan.audio_mode == AudioMode.COPY:
            args += ["-c:a", "copy"]
        elif chan.audio_mode == AudioMode.DISABLE:
            args += ["-an"]
        else:
            args += ["-c:a", chan.audio_codec or "aac"]

        # ------------------------
        # Purpose-specific handling
        # ------------------------
        if self.purpose == "live_forward":
            # Forward live input to an output
            if chan.output_type == "hls":
                # HLS output_target is treated as a directory.
                out_dir = Path(raw_output_target)
                if not out_dir.is_absolute():
                    out_dir = Path(settings.MEDIA_ROOT) / out_dir
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
                # Network URL, use as-is
                args += ["-f", "flv", raw_output_target]

            elif chan.output_type == "udp_ts":
                # Network URL, use as-is
                args += ["-f", "mpegts", raw_output_target]

            else:
                # Fallback: treat output_target as a file path (relative to MEDIA_ROOT if not absolute)
                out_path = Path(raw_output_target)
                if not out_path.is_absolute():
                    out_path = Path(settings.MEDIA_ROOT) / out_path
                args += ["-f", "mpegts", str(out_path)]

        elif self.purpose == "record":
            # Record to disk in TS segments using recording_path_template
            from datetime import datetime

            now = datetime.now()
            date_str = now.strftime("%Y%m%d")

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

            # Example filename pattern: <channel>_00001.ts, <channel>_00002.ts, ...
            segment_pattern = str(base_dir / f"{chan.name}_%05d.ts")

            segment_seconds = chan.recording_segment_minutes * 60

            args += [
                "-f", "segment",
                "-segment_time", str(segment_seconds),
                "-reset_timestamps", "1",
                segment_pattern,
            ]

        # We'll add "playback" cases later (for time-shift).
        return args


def build_ffmpeg_cmd_for_channel(channel_id: int, purpose: str = "live_forward") -> str:
    """
    Helper: loads the Channel and returns a shell-safe ffmpeg command string.
    """
    chan = Channel.objects.get(pk=channel_id)
    job = FFmpegJobConfig(channel=chan, purpose=purpose)
    cmd_list = job.build_command()
    return " ".join(shlex.quote(part) for part in cmd_list)
