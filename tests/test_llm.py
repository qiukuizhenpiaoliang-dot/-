import unittest

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from job_apply_assistant.config import Profile
from job_apply_assistant.llm import extract_keywords, infer_role, local_generate_draft


class LocalDraftTests(unittest.TestCase):
    def test_extract_keywords(self):
        jd = "需要熟悉 Python、SQL 和数据分析，能够跨部门沟通。"
        self.assertEqual(extract_keywords(jd), ["Python", "SQL", "数据分析", "沟通", "跨部门"])

    def test_infer_role_from_jd(self):
        jd = "招聘岗位：产品运营实习生\n岗位职责：用户研究和竞品分析"
        self.assertEqual(infer_role(jd), "产品运营实习生")

    def test_local_generate_contains_profile_and_structure(self):
        profile = Profile(
            name="张三",
            school="某某大学",
            graduation_year="2027",
            major="数据科学",
            availability="一周内到岗",
            internship_period="可连续实习 4 个月",
            summary="做过数据分析和自动化项目。",
            highlights=["用 Python 完成数据清洗并输出分析报告。"],
        )
        draft = local_generate_draft(
            "招聘岗位：数据分析实习生，需要 Python、SQL、Excel。",
            "hr@example.com",
            profile,
        )
        self.assertIn("某某大学2027届数据科学数据分析实习生岗位投递", draft.title)
        self.assertIn("HR您好", draft.body)
        self.assertIn("Python", draft.jd_keywords)


if __name__ == "__main__":
    unittest.main()
