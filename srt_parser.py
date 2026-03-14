import re
from dataclasses import dataclass


@dataclass
class Subtitle:
    index: int
    start_seconds: float
    end_seconds: float
    text: str


def _timestamp_to_seconds(ts: str) -> float:
    """Convert SRT timestamp (HH:MM:SS,mmm) to seconds."""
    h, m, s = ts.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def parse_srt(file_path: str) -> list[Subtitle]:
    """Parse an SRT file and return a list of Subtitle objects."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        r"(\d+)\s*\n"
        r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*\n"
        r"((?:.+\n?)+)",
        re.MULTILINE,
    )

    subtitles = []
    for match in pattern.finditer(content):
        index = int(match.group(1))
        start = _timestamp_to_seconds(match.group(2))
        end = _timestamp_to_seconds(match.group(3))
        text = match.group(4).strip().replace("\n", " ")
        subtitles.append(Subtitle(index=index, start_seconds=start, end_seconds=end, text=text))

    return subtitles


def format_timestamp(seconds: float) -> str:
    """Format seconds as MM:SS for display."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"
