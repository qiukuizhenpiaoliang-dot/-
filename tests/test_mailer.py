import tempfile
import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from job_apply_assistant.config import Settings
from job_apply_assistant.mailer import MailerError, build_message


class MailerTests(unittest.TestCase):
    def test_build_message_attaches_resume(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            resume = Path(temp_dir) / "resume.pdf"
            resume.write_bytes(b"%PDF-1.4 test")
            settings = Settings(
                sender_email="me@example.com",
                sender_name="张三",
                smtp_username="me@example.com",
                resume_path=str(resume),
            )
            message = build_message(
                settings=settings,
                to_email="hr@example.com",
                subject="投递标题",
                body="正文",
            )
            self.assertEqual(message["To"], "hr@example.com")
            self.assertEqual(message.get_payload()[-1].get_filename(), "resume.pdf")

    def test_build_message_requires_resume(self):
        settings = Settings(sender_email="me@example.com")
        with self.assertRaises(MailerError):
            build_message(
                settings=settings,
                to_email="hr@example.com",
                subject="投递标题",
                body="正文",
            )


if __name__ == "__main__":
    unittest.main()
