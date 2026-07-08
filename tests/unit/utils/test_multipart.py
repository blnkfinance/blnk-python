"""Unit tests for `MultipartBody` (4 cases): multipart type detection,
buffer- and file-stream-backed part encoding with header shape, and a real
transport round-trip against a loopback HTTP server.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from blnk_sdk.http_client import read_response_json_body
from blnk_sdk.multipart import MultipartBody, is_multipart_body
from blnk_sdk.transport import TransportRequest, RequestsTransport
from tests.mocks.stream_test_utils import read_stream_body


def test_is_multipart_body_identifies_multipart_instances() -> None:
    assert is_multipart_body(MultipartBody())
    assert not is_multipart_body({})


def test_multipart_body_encodes_buffer_backed_parts() -> None:
    form_data = MultipartBody()
    form_data.append("source", "stripe")
    form_data.append("file", b"a,b,c", filename="test.csv")

    payload = read_stream_body(form_data)
    headers = form_data.get_headers()

    assert re.search(r"stripe", payload)
    assert re.search(r"a,b,c", payload)
    assert re.search(r"multipart/form-data", headers["content-type"])


def test_multipart_body_encodes_file_stream_parts(tmp_path) -> None:
    file_path = tmp_path / "upload.csv"
    file_path.write_text("amount,ref\n100,abc")

    form_data = MultipartBody()
    form_data.append("source", "stripe")
    form_data.append("file", open(file_path, "rb"), filename="upload.csv")

    payload = read_stream_body(form_data)
    headers = form_data.get_headers()

    assert re.search(r"stripe", payload)
    assert re.search(r"amount,ref", payload)
    assert re.search(r"100,abc", payload)
    assert re.search(r"multipart/form-data", headers["content-type"])


def test_real_transport_accepts_multipart_body_against_loopback_server(
    tmp_path,
) -> None:
    file_path = tmp_path / "upload.csv"
    file_path.write_text("amount,ref\n300,native")

    form_data = MultipartBody()
    form_data.append("source", "stripe")
    form_data.append("file", open(file_path, "rb"), filename="upload.csv")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 (http.server API)
            length = int(self.headers.get("Content-Length", "0"))
            payload = self.rfile.read(length).decode("utf-8")
            body = json.dumps(
                {"ok": "stripe" in payload and "300,native" in payload}
            ).encode("utf-8")
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence request logging
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    transport = RequestsTransport()
    try:
        port = server.server_address[1]
        init = TransportRequest(
            method="POST",
            headers=form_data.get_headers(),
            body=form_data,
            timeout_ms=10000,
        )
        response = transport(f"http://127.0.0.1:{port}/upload", init)

        assert response.status == 201
        result = read_response_json_body(response)
        assert result["ok"]
    finally:
        transport.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
