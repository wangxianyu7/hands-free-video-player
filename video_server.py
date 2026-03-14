"""Lightweight HTTP server to serve video files for the HTML5 player."""

import os
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler


class VideoHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress log output

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()


_server = None
_port = 8502


def start_video_server(directory: str, port: int = 8502) -> int:
    """Start a background HTTP server serving files from the given directory.
    Returns the port number."""
    global _server, _port
    _port = port

    if _server is not None:
        return _port

    handler = partial(VideoHandler, directory=directory)
    _server = HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    return _port


def get_video_url(filename: str) -> str:
    """Get the URL for a video file served by the local server."""
    from urllib.parse import quote
    return f"http://127.0.0.1:{_port}/{quote(filename)}"
