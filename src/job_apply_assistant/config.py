from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_PROFILE: Dict[str, Any] = {
    "name": "",
    "school": "",
    "graduation_year": "",
    "major": "",
    "target_role": "",
    "availability": "",
    "internship_period": "",
    "phone": "",
    "contact_email": "",
    "summary": "",
    "highlights": [],
}


def load_dotenv(path: Optional[Path] = None) -> None:
    env_path = path or (PROJECT_ROOT / ".env")
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        os.environ[key] = value


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_path(value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@dataclass
class Settings:
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-5.4-mini"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_starttls: bool = False
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    sender_name: str = ""
    resume_path: str = ""
    profile_path: str = "config/profile.json"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        port_text = os.getenv("SMTP_PORT", "465").strip() or "465"
        try:
            smtp_port = int(port_text)
        except ValueError:
            smtp_port = 465

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip(),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini") or "gpt-5.4-mini",
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=smtp_port,
            smtp_use_ssl=parse_bool(os.getenv("SMTP_USE_SSL"), True),
            smtp_starttls=parse_bool(os.getenv("SMTP_STARTTLS"), False),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            sender_email=os.getenv("SENDER_EMAIL", ""),
            sender_name=os.getenv("SENDER_NAME", ""),
            resume_path=os.getenv("RESUME_PATH", ""),
            profile_path=os.getenv("PROFILE_PATH", "config/profile.json")
            or "config/profile.json",
        )

    def public_state(self) -> Dict[str, Any]:
        resume = resolve_path(self.resume_path) if self.resume_path else None
        return {
            "openai_configured": bool(self.openai_api_key),
            "openai_base_url": self.openai_base_url,
            "openai_model": self.openai_model,
            "smtp_configured": bool(
                self.smtp_host
                and self.smtp_port
                and self.smtp_username
                and self.smtp_password
                and (self.sender_email or self.smtp_username)
            ),
            "sender_email": self.sender_email or self.smtp_username,
            "sender_name": self.sender_name,
            "resume_path": str(resume) if resume else "",
            "resume_exists": bool(resume and resume.exists() and resume.is_file()),
        }


@dataclass
class Profile:
    name: str = ""
    school: str = ""
    graduation_year: str = ""
    major: str = ""
    target_role: str = ""
    availability: str = ""
    internship_period: str = ""
    phone: str = ""
    contact_email: str = ""
    summary: str = ""
    highlights: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        merged = {**DEFAULT_PROFILE, **(data or {})}
        highlights = merged.get("highlights", [])
        if isinstance(highlights, str):
            highlights = [line.strip() for line in highlights.splitlines() if line.strip()]
        elif not isinstance(highlights, list):
            highlights = []

        return cls(
            name=str(merged.get("name", "")).strip(),
            school=str(merged.get("school", "")).strip(),
            graduation_year=str(merged.get("graduation_year", "")).strip(),
            major=str(merged.get("major", "")).strip(),
            target_role=str(merged.get("target_role", "")).strip(),
            availability=str(merged.get("availability", "")).strip(),
            internship_period=str(merged.get("internship_period", "")).strip(),
            phone=str(merged.get("phone", "")).strip(),
            contact_email=str(merged.get("contact_email", "")).strip(),
            summary=str(merged.get("summary", "")).strip(),
            highlights=[str(item).strip() for item in highlights if str(item).strip()],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "school": self.school,
            "graduation_year": self.graduation_year,
            "major": self.major,
            "target_role": self.target_role,
            "availability": self.availability,
            "internship_period": self.internship_period,
            "phone": self.phone,
            "contact_email": self.contact_email,
            "summary": self.summary,
            "highlights": self.highlights,
        }

    def display_identity(self) -> str:
        parts = [
            self.school,
            f"{self.graduation_year}届" if self.graduation_year else "",
            self.major,
        ]
        return "".join(part for part in parts if part)


def load_profile(settings: Optional[Settings] = None) -> Profile:
    active_settings = settings or Settings.from_env()
    candidates = [
        resolve_path(active_settings.profile_path),
        PROJECT_ROOT / "config" / "profile.example.json",
    ]

    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        return Profile.from_dict(data)

    return Profile()
