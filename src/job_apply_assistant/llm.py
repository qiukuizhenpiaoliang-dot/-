from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional

from .config import Profile, Settings


KEYWORD_CANDIDATES = [
    "Python",
    "SQL",
    "Excel",
    "PowerPoint",
    "Tableau",
    "Power BI",
    "数据分析",
    "用户研究",
    "竞品分析",
    "市场调研",
    "内容运营",
    "用户运营",
    "新媒体",
    "产品",
    "项目管理",
    "AIGC",
    "LLM",
    "大模型",
    "提示词",
    "自动化",
    "爬虫",
    "沟通",
    "跨部门",
    "英语",
    "实习",
]


ROLE_PATTERNS = [
    r"(?:岗位|职位|招聘岗位|应聘职位)[:：\s]*([\u4e00-\u9fa5A-Za-z0-9+/（）()·\- ]{2,30})",
    r"([\u4e00-\u9fa5A-Za-z0-9+/（）()·\- ]{2,24})(?:实习生|intern|Intern)",
]


@dataclass
class DraftResult:
    title: str
    body: str
    match_points: List[str] = field(default_factory=list)
    jd_keywords: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    provider: str = "local-demo"

    @classmethod
    def from_dict(cls, data: Dict[str, Any], provider: str) -> "DraftResult":
        title = (
            data.get("title")
            or data.get("subject")
            or data.get("email_subject")
            or data.get("mail_subject")
            or ""
        )
        body = (
            data.get("body")
            or data.get("email_body")
            or data.get("content")
            or data.get("mail_body")
            or ""
        )
        return cls(
            title=str(title).strip(),
            body=str(body).strip(),
            match_points=_string_list(data.get("match_points", [])),
            jd_keywords=_string_list(data.get("jd_keywords", [])),
            risk_notes=_string_list(data.get("risk_notes", [])),
            provider=provider,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "body": self.body,
            "match_points": self.match_points,
            "jd_keywords": self.jd_keywords,
            "risk_notes": self.risk_notes,
            "provider": self.provider,
        }


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_keywords(jd_text: str) -> List[str]:
    lowered = jd_text.lower()
    found = []
    for keyword in KEYWORD_CANDIDATES:
        if keyword.lower() in lowered or keyword in jd_text:
            found.append(keyword)
    return found[:8]


def infer_role(jd_text: str, fallback: str = "") -> str:
    for pattern in ROLE_PATTERNS:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            role = normalize_spaces(match.group(1))
            role = re.sub(r"[，。；;,.].*$", "", role).strip()
            if role:
                if "实习" not in role and re.search(r"实习生|intern", match.group(0), re.I):
                    role = f"{role}实习生"
                return role[:28]
    return fallback or "相关"


def build_title(profile: Profile, role: str) -> str:
    school = profile.school or "某某学校"
    year = f"{profile.graduation_year}届" if profile.graduation_year else "某某级"
    major = profile.major or "某某专业"
    availability = profile.availability or "可尽快到岗"
    period = profile.internship_period or "可稳定实习"
    return f"{school}{year}{major}{role}岗位投递｜{availability}｜{period}"


def local_generate_draft(
    jd_text: str,
    hr_email: str,
    profile: Profile,
    company: str = "",
    target_role: str = "",
    warning: Optional[str] = None,
) -> DraftResult:
    role = target_role.strip() or infer_role(jd_text, profile.target_role)
    keywords = extract_keywords(jd_text)
    highlights = profile.highlights[:3] or [
        "具备与岗位要求相关的项目实践和快速学习能力",
        "能够围绕目标拆解任务、沉淀方法并按时交付",
        "重视沟通协作，可根据业务反馈快速迭代产出",
    ]
    identity = profile.display_identity() or "候选人"
    name = profile.name or "候选人"
    company_phrase = f"贵司{company}" if company else "贵司"
    keyword_text = "、".join(keywords[:5]) if keywords else "岗位要求"

    body = "\n".join(
        [
            "HR您好：",
            "",
            f"我是{name}，{identity}，关注到{company_phrase}{role}岗位后非常感兴趣。结合 JD 中对{keyword_text}等能力的要求，我认为自己的背景与岗位需求有较高匹配度，特此投递简历。",
            "",
            f"首先，我的背景与岗位核心任务相关。{profile.summary or highlights[0]}",
            f"其次，我有可迁移的项目与执行经验。{highlights[0]}",
            f"另外，我能够稳定投入并快速进入工作状态。{profile.availability or '我可以尽快到岗'}，{profile.internship_period or '可保持稳定实习时间'}。",
            "",
            f"如果有机会进一步沟通，我很愿意结合{role}岗位的具体业务目标介绍更多项目细节。感谢您的时间，期待回复。",
            "",
            f"{name}",
            profile.phone,
            profile.contact_email,
        ]
    )
    body = "\n".join(line for line in body.splitlines() if line is not None)

    risk_notes = []
    if warning:
        risk_notes.append(warning)
    if not profile.highlights:
        risk_notes.append("当前个人亮点为空，正文使用了通用表达；建议补充项目、实习或量化成果。")
    if not keywords:
        risk_notes.append("未识别到明显 JD 关键词，建议检查 JD 文本是否完整。")

    return DraftResult(
        title=build_title(profile, role),
        body=body,
        match_points=[
            f"标题已覆盖学校、届别、专业、岗位、到岗时间和实习周期：{role}",
            f"正文围绕 JD 关键词展开：{keyword_text}",
            "正文使用总-分-总结构，并保留发送前人工编辑空间。",
        ],
        jd_keywords=keywords,
        risk_notes=risk_notes,
        provider="local-demo",
    )


DRAFT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Highly targeted Chinese email subject line.",
        },
        "body": {
            "type": "string",
            "description": "Chinese job application email body in 总-分-总 structure.",
        },
    },
    "required": ["title", "body"],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """你是中文求职投递邮件写作 Agent。你的任务是基于用户背景和 JD，撰写高针对性的求职投递邮件。

要求：
1. 不改动、不解读简历附件，只使用用户提供的背景和 JD 文本。
2. 不能虚构学校、经历、成果、工具、奖项、公司或时间。
3. 邮件标题必须包含：学校、届别或年级、专业、岗位、到岗时间、实习周期。
4. 正文采用“总-分-总”结构：礼貌自我介绍；分点回应 JD 痛点；最后表达期待沟通。
5. 语言要自然、克制、专业，避免夸张营销腔。
6. 输出 JSON 必须只包含 title 和 body 两个字段。
7. 背景信息不足时用保守措辞，不要用编造内容补齐。
"""


def build_user_prompt(
    jd_text: str,
    hr_email: str,
    profile: Profile,
    company: str = "",
    target_role: str = "",
) -> str:
    payload = {
        "hr_email": hr_email,
        "company": company,
        "target_role": target_role,
        "profile": profile.to_dict(),
        "jd_text": jd_text,
    }
    return (
        "请根据以下 JSON 输入生成投递邮件。只输出 JSON 对象，不要输出 Markdown。"
        "\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def extract_json_object(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def create_openai_client(settings: Settings) -> Any:
    from openai import OpenAI

    kwargs: Dict[str, Any] = {
        "api_key": settings.openai_api_key,
        "timeout": 45,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)


def generate_with_chat_completions(
    client: Any,
    model: str,
    jd_text: str,
    hr_email: str,
    profile: Profile,
    company: str = "",
    target_role: str = "",
) -> DraftResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_user_prompt(
                jd_text,
                hr_email,
                profile,
                company=company,
                target_role=target_role,
            ),
        },
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=1800,
            temperature=0.2,
        )
    except Exception:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1800,
            temperature=0.2,
        )

    content = response.choices[0].message.content
    data = extract_json_object(content)
    return DraftResult.from_dict(data, provider=f"openai-compatible:{model}")


def generate_draft(
    jd_text: str,
    hr_email: str,
    profile: Profile,
    settings: Optional[Settings] = None,
    company: str = "",
    target_role: str = "",
) -> DraftResult:
    active_settings = settings or Settings.from_env()
    jd_text = jd_text.strip()
    hr_email = hr_email.strip()

    if not active_settings.openai_api_key:
        return local_generate_draft(
            jd_text,
            hr_email,
            profile,
            company=company,
            target_role=target_role,
            warning="未配置 OPENAI_API_KEY，当前为本地预览生成。",
        )

    try:
        from openai import OpenAI
    except Exception as exc:
        return local_generate_draft(
            jd_text,
            hr_email,
            profile,
            company=company,
            target_role=target_role,
            warning=f"未能加载 openai SDK，已切换本地预览：{exc}",
        )

    try:
        client = create_openai_client(active_settings)
    except Exception as exc:
        return local_generate_draft(
            jd_text,
            hr_email,
            profile,
            company=company,
            target_role=target_role,
            warning=f"未能初始化 AI 客户端，已切换本地预览：{exc}",
        )

    if active_settings.openai_base_url:
        result = generate_with_chat_completions(
            client,
            active_settings.openai_model,
            jd_text,
            hr_email,
            profile,
            company=company,
            target_role=target_role,
        )
        if not result.title or not result.body:
            raise ValueError("模型返回内容不完整，请重试或检查输入。")
        return result

    response = client.responses.create(
        model=active_settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    jd_text,
                    hr_email,
                    profile,
                    company=company,
                    target_role=target_role,
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "job_application_draft",
                "schema": DRAFT_SCHEMA,
                "strict": True,
            }
        },
        max_output_tokens=1800,
    )

    data = json.loads(response.output_text)
    result = DraftResult.from_dict(data, provider=f"openai:{active_settings.openai_model}")
    if not result.title or not result.body:
        raise ValueError("模型返回内容不完整，请重试或检查输入。")
    return result
