from __future__ import annotations

import argparse
import base64
import binascii
from http import HTTPStatus
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Tuple
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import PROJECT_ROOT, Profile, Settings, load_profile
from .llm import generate_draft
from .mailer import MailerError, send_mail


WEB_ROOT = PROJECT_ROOT / "web"
UPLOAD_ROOT = PROJECT_ROOT / "resumes"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_RESUME_SUFFIXES = {".pdf", ".doc", ".docx"}


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


class AssistantHandler(BaseHTTPRequestHandler):
    server_version = "JobApplyAssistant/0.1"

    def do_HEAD(self) -> None:
        route = self._static_route()
        if route:
            path, content_type = route
            self._send_file(path, content_type, head_only=True)
            return
        if self.path == "/healthz":
            self._send_json({"ok": True}, head_only=True)
            return
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        try:
            route = self._static_route()
            if route:
                path, content_type = route
                self._send_file(path, content_type)
                return
            if self.path == "/healthz":
                self._send_json({"ok": True})
                return
            if self.path == "/api/profile":
                self._send_json(
                    {
                        "profile": load_profile(self.server.settings).to_dict(),
                        "settings": self.server.settings.public_state(),
                    }
                )
                return
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_POST(self) -> None:
        try:
            if self.path == "/api/draft":
                payload = self._read_json()
                jd_text, hr_email, company, target_role, profile = self._draft_inputs(payload)
                result = generate_draft(
                    jd_text,
                    hr_email,
                    profile,
                    self.server.settings,
                    company=company,
                    target_role=target_role,
                )
                self._send_json({"draft": result.to_dict()})
                return

            if self.path == "/api/send":
                payload = self._read_json()
                result = send_mail(
                    settings=self.server.settings,
                    to_email=str(payload.get("hr_email", "")),
                    subject=str(payload.get("subject", "")),
                    body=str(payload.get("body", "")),
                    attachment_path=str(payload.get("resume_path", "")).strip() or None,
                )
                self._send_json({"sent": result.to_dict()})
                return

            if self.path == "/api/upload-resume":
                payload = self._read_json()
                uploaded = self._save_resume_upload(payload)
                self._send_json({"resume": uploaded})
                return

            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
        except ApiError as exc:
            self._send_json({"error": exc.message}, status=exc.status)
        except MailerError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), format % args))

    def _draft_inputs(self, payload: Dict[str, Any]) -> Tuple[str, str, str, str, Profile]:
        jd_text = str(payload.get("jd_text", "")).strip()
        hr_email = str(payload.get("hr_email", "")).strip()
        company = str(payload.get("company", "")).strip()
        target_role = str(payload.get("target_role", "")).strip()
        if len(jd_text) < 20:
            raise ApiError("JD 文本过短，请粘贴完整职位描述。")
        if "@" not in hr_email:
            raise ApiError("请填写有效的 HR 接收邮箱。")
        profile_payload = payload.get("profile", {})
        profile = Profile.from_dict(profile_payload if isinstance(profile_payload, dict) else {})
        return jd_text, hr_email, company, target_role, profile

    def _static_route(self) -> Tuple[Path, str]:
        if self.path in {"/", "/index.html"}:
            return WEB_ROOT / "index.html", "text/html; charset=utf-8"
        if self.path == "/assets/styles.css":
            return WEB_ROOT / "assets" / "styles.css", "text/css; charset=utf-8"
        if self.path == "/assets/app.js":
            return WEB_ROOT / "assets" / "app.js", "application/javascript; charset=utf-8"
        return ()

    def _save_resume_upload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        filename = str(payload.get("filename", "")).strip()
        data_base64 = str(payload.get("data_base64", "")).strip()
        if not filename:
            raise ApiError("缺少简历文件名。")
        if not data_base64:
            raise ApiError("缺少简历文件内容。")

        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_RESUME_SUFFIXES:
            raise ApiError("简历仅支持 PDF、DOC、DOCX。")

        try:
            content = base64.b64decode(data_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ApiError("简历文件内容解析失败。") from exc
        if not content:
            raise ApiError("简历文件为空。")
        if len(content) > MAX_UPLOAD_BYTES:
            raise ApiError("简历文件超过 25MB。")

        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem or "resume"
        safe_stem = re.sub(r"[^\w\u4e00-\u9fa5.\- ]+", "_", stem).strip(" ._")
        safe_stem = safe_stem or "resume"
        target = UPLOAD_ROOT / f"{int(time.time())}_{safe_stem}{suffix}"
        target.write_bytes(content)

        return {
            "filename": target.name,
            "path": str(target),
            "size": len(content),
        }

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ApiError(f"JSON 格式错误：{exc}") from exc
        if not isinstance(data, dict):
            raise ApiError("请求体必须是 JSON 对象。")
        return data

    def _send_json(
        self,
        payload: Dict[str, Any],
        status: int = HTTPStatus.OK,
        head_only: bool = False,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str, head_only: bool = False) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head_only:
            self.wfile.write(body)


class AssistantServer(ThreadingHTTPServer):
    def __init__(self, server_address: Tuple[str, int], handler_class: Any, settings: Settings):
        super().__init__(server_address, handler_class)
        self.settings = settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="智能求职投递助手")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env()
    server = AssistantServer((args.host, args.port), AssistantHandler, settings=settings)
    print(f"智能求职投递助手已启动：http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止服务。")
    finally:
        server.server_close()
