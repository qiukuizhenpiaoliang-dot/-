import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from job_apply_assistant.llm import DraftResult, extract_json_object


class CompatibleAiTests(unittest.TestCase):
    def test_maps_subject_to_title(self):
        draft = DraftResult.from_dict(
            {"subject": "投递标题", "body": "正文"},
            provider="test",
        )
        self.assertEqual(draft.title, "投递标题")
        self.assertEqual(draft.body, "正文")

    def test_extracts_json_from_markdown(self):
        data = extract_json_object('```json\n{"title":"标题","body":"正文"}\n```')
        self.assertEqual(data["title"], "标题")


if __name__ == "__main__":
    unittest.main()
