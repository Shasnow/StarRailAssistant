from __future__ import annotations

import json
from typing import Any


def build_multipart_body(
    fields: dict[str, str],
    file_field: str,
    filename: str,
    content_type: str,
    data: bytes,
    boundary: str,
) -> bytes:
    crlf = b"\r\n"
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.extend([
            b"--" + boundary.encode(),
            b'Content-Disposition: form-data; name="' + key.encode() + b'"',
            b"",
            value.encode(),
        ])
    parts.extend([
        b"--" + boundary.encode(),
        b'Content-Disposition: form-data; name="' + file_field.encode() + b'"; filename="' + filename.encode() + b'"',
        b"Content-Type: " + content_type.encode(),
        b"",
        data,
        b"--" + boundary.encode() + b"--",
        b"",
    ])
    return crlf.join(parts)


def load_json_object(body: str) -> dict[str, Any] | None:
    if not body:
        return None
    try:
        data = json.loads(body)
    except Exception:
        return None
    return data if isinstance(data, dict) else None

