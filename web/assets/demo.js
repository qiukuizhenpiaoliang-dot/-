const state = {
  draftReady: false,
};

const keywordCandidates = [
  "Python",
  "SQL",
  "Excel",
  "PowerPoint",
  "数据分析",
  "用户研究",
  "竞品分析",
  "市场调研",
  "内容运营",
  "产品",
  "项目管理",
  "AIGC",
  "大模型",
  "自动化",
  "沟通",
  "跨部门",
  "实习",
];

const sampleText = `公司：澜一科技
投递邮箱：hr@example.com
岗位：AI 产品运营实习生
简历：demo-resume.pdf
JD：
岗位职责：
1. 参与 AI 工具产品的用户调研、需求梳理和竞品分析；
2. 使用 Excel、SQL 或 Python 处理运营数据，输出分析报告；
3. 协助沉淀 SOP、优化投递和运营自动化流程。
岗位要求：
1. 可连续实习 3 个月以上，沟通能力好；
2. 对 AIGC、大模型和效率工具有兴趣；
3. 有产品、运营、数据分析或项目管理经验优先。`;

const el = (id) => document.getElementById(id);

function toast(message) {
  const node = el("toast");
  node.textContent = message;
  node.classList.add("visible");
  window.clearTimeout(node.dataset.timer);
  node.dataset.timer = window.setTimeout(() => {
    node.classList.remove("visible");
  }, 3200);
}

function setStatus(id, text, ok) {
  const node = el(id);
  node.textContent = text;
  node.classList.remove("ok", "warn");
  node.classList.add(ok ? "ok" : "warn");
}

function setLoading(button, loading, text) {
  if (!button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  button.disabled = loading;
  button.textContent = loading ? text : button.dataset.label;
}

function linesFromTextarea(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function collectProfile() {
  return {
    name: el("profileName").value.trim() || "候选人",
    school: el("profileSchool").value.trim() || "某某学校",
    graduation_year: el("profileYear").value.trim() || "2027",
    major: el("profileMajor").value.trim() || "某某专业",
    availability: el("profileAvailability").value.trim() || "一周内到岗",
    internship_period: el("profilePeriod").value.trim() || "可连续实习 3 个月以上",
    phone: el("profilePhone").value.trim(),
    contact_email: el("profileEmail").value.trim(),
    summary: el("profileSummary").value.trim(),
    highlights: linesFromTextarea(el("profileHighlights").value),
  };
}

function firstMatch(text, patterns) {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match && match[1]) {
      return match[1].trim().replace(/[，,。；;]+$/, "");
    }
  }
  return "";
}

function extractSmartFields(text) {
  const email = firstMatch(text, [
    /(?:邮箱|HR邮箱|接收邮箱|投递邮箱|email)[:：\s]*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/i,
    /([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})/i,
  ]);
  const company = firstMatch(text, [
    /(?:公司|公司名称|企业|单位|部门)[:：\s]*([^\n\r，,；;]{2,60})/i,
  ]);
  const role = firstMatch(text, [
    /(?:岗位|职位|应聘岗位|投递岗位|目标岗位)[:：\s]*([^\n\r，,；;]{2,60})/i,
    /([^\n\r，,；;]{2,40}(?:实习生|intern))/i,
  ]);
  const resumePath = firstMatch(text, [
    /(?:简历|附件|resume)[:：\s]*([^\n\r]+\.(?:pdf|docx?|PDF|DOCX?))/i,
    /((?:\/Users\/|\/|[A-Za-z]:\\|demo-)[^\n\r]+\.(?:pdf|docx?|PDF|DOCX?))/i,
  ]);

  const lines = text.split(/\r?\n/);
  const jdStart = lines.findIndex((line) =>
    /^(?:JD|职位描述|岗位描述|岗位职责|岗位要求|工作职责|任职要求)[:：\s]*/i.test(
      line.trim(),
    ),
  );
  let jdText = "";
  if (jdStart >= 0) {
    jdText = lines.slice(jdStart).join("\n");
    jdText = jdText.replace(
      /^(?:JD|职位描述|岗位描述|岗位职责|岗位要求|工作职责|任职要求)[:：\s]*/i,
      "",
    );
  } else {
    jdText = lines
      .filter((line) => {
        const trimmed = line.trim();
        if (!trimmed) return false;
        if (email && trimmed.includes(email)) return false;
        if (resumePath && trimmed.includes(resumePath)) return false;
        return !/^(?:公司|公司名称|企业|单位|部门|邮箱|HR邮箱|接收邮箱|投递邮箱|简历|附件|岗位|职位|应聘岗位|投递岗位|目标岗位)[:：]/i.test(
          trimmed,
        );
      })
      .join("\n")
      .trim();
  }

  return {
    email,
    company,
    role,
    resumePath,
    jdText: jdText.trim(),
  };
}

function applySmartFields(fields) {
  let count = 0;
  if (fields.email) {
    el("hrEmail").value = fields.email;
    count += 1;
  }
  if (fields.company) {
    el("company").value = fields.company;
    count += 1;
  }
  if (fields.role) {
    el("targetRole").value = fields.role;
    count += 1;
  }
  if (fields.resumePath) {
    el("resumePath").value = fields.resumePath;
    updateResumeDisplay(fields.resumePath);
    count += 1;
  }
  if (fields.jdText && fields.jdText.length > 20) {
    el("jdText").value = fields.jdText;
    count += 1;
  }
  toast(count ? `已拆分 ${count} 个字段` : "没有识别到可填字段");
}

function extractKeywords(jdText) {
  const lower = jdText.toLowerCase();
  return keywordCandidates
    .filter((keyword) => lower.includes(keyword.toLowerCase()) || jdText.includes(keyword))
    .slice(0, 6);
}

function inferRole(jdText) {
  const explicit = el("targetRole").value.trim();
  if (explicit) return explicit;
  const match = jdText.match(/(?:岗位|职位|招聘岗位)[:：\s]*([^\n\r，,；;。]{2,30})/);
  if (match) return match[1].trim();
  const intern = jdText.match(/([^\n\r，,；;。]{2,24}(?:实习生|intern))/i);
  return intern ? intern[1].trim() : "相关";
}

function generateLocalDraft() {
  const jdText = el("jdText").value.trim();
  const hrEmail = el("hrEmail").value.trim();
  if (!hrEmail.includes("@")) {
    throw new Error("请填写有效的 HR 邮箱");
  }
  if (jdText.length < 20) {
    throw new Error("请粘贴完整 JD");
  }

  const profile = collectProfile();
  const role = inferRole(jdText);
  const company = el("company").value.trim();
  const keywords = extractKeywords(jdText);
  const keywordText = keywords.length ? keywords.join("、") : "岗位要求";
  const highlights = profile.highlights.length
    ? profile.highlights
    : [
        "具备与岗位相关的项目实践、信息整理和快速学习能力",
        "能够围绕目标拆解任务，按时交付并根据反馈迭代",
      ];

  const title = `${profile.school}${profile.graduation_year}届${profile.major}${role}岗位投递｜${profile.availability}｜${profile.internship_period}`;
  const body = [
    "HR您好：",
    "",
    `我是${profile.name}，${profile.school}${profile.graduation_year}届${profile.major}，关注到${company || "贵司"}${role}岗位后非常感兴趣。结合 JD 中对${keywordText}等能力的要求，我认为自己的背景与岗位需求有较高匹配度，特此投递简历。`,
    "",
    `首先，我的背景与岗位核心任务相关。${profile.summary || highlights[0]}`,
    `其次，我有可迁移的项目与执行经验。${highlights[0]}`,
    `另外，我能够稳定投入并快速进入工作状态。${profile.availability}，${profile.internship_period}。`,
    "",
    `如果有机会进一步沟通，我很愿意结合${role}岗位的具体业务目标介绍更多项目细节。感谢您的时间，期待回复。`,
    "",
    profile.name,
    profile.phone,
    profile.contact_email,
  ]
    .filter((line) => line !== undefined)
    .join("\n");

  return { title, body };
}

async function generateDraft() {
  const button = el("generateBtn");
  setLoading(button, true, "生成中");
  try {
    await new Promise((resolve) => window.setTimeout(resolve, 360));
    const draft = generateLocalDraft();
    el("subjectPreview").value = draft.title;
    el("bodyPreview").value = draft.body;
    state.draftReady = true;
    el("sendBtn").disabled = false;
    toast("已生成演示邮件");
  } catch (error) {
    toast(error.message);
  } finally {
    setLoading(button, false);
  }
}

async function sendMail() {
  if (!state.draftReady) {
    toast("请先生成或填写邮件内容");
    return;
  }
  window.alert("GitHub Pages 演示版不会真实发送邮件。真实发送请在本地运行 Python 版本。");
}

async function copyText(id, label) {
  const value = el(id).value;
  if (!value.trim()) {
    toast(`${label}为空`);
    return;
  }
  await navigator.clipboard.writeText(value);
  toast(`已复制${label}`);
}

async function readClipboardAndParse() {
  try {
    const text = await navigator.clipboard.readText();
    el("smartPasteBox").value = text;
    applySmartFields(extractSmartFields(text));
  } catch (error) {
    toast("无法读取剪贴板，请手动粘贴后拆分");
  }
}

function updateResumeDisplay(pathOrName) {
  const fileName = pathOrName.split(/[\\/]/).pop() || pathOrName;
  el("resumeDropTitle").textContent = fileName;
  el("resumeDropMeta").textContent = pathOrName;
  setStatus("resumeStatus", "简历已选择", true);
}

function uploadResumeFile(file) {
  if (!file) return;
  const suffix = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "doc", "docx"].includes(suffix)) {
    toast("简历仅支持 PDF、DOC、DOCX");
    return;
  }
  el("resumePath").value = file.name;
  updateResumeDisplay(file.name);
  toast("演示版已读取文件名");
}

function fillSample() {
  el("smartPasteBox").value = sampleText;
  applySmartFields(extractSmartFields(sampleText));
  el("profileName").value = "张同学";
  el("profileSchool").value = "示例大学";
  el("profileYear").value = "2027";
  el("profileMajor").value = "数字媒体技术";
  el("profileAvailability").value = "一周内到岗";
  el("profilePeriod").value = "可连续实习 3 个月以上";
  el("profilePhone").value = "138****0000";
  el("profileEmail").value = "candidate@example.com";
  el("profileSummary").value = "具备 AIGC 工具应用、内容分析和自动化流程搭建经验，能够从需求拆解到交付复盘完成完整项目。";
  el("profileHighlights").value = [
    "独立搭建智能求职投递助手，完成 JD 解析、邮件生成和 SMTP 发送流程。",
    "熟悉 Excel、Python 和 AIGC 工具，可输出结构化分析报告。",
  ].join("\n");
}

function initResumeUpload() {
  const zone = el("resumeDropzone");
  const input = el("resumeFileInput");
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", () => uploadResumeFile(input.files[0]));

  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("drag-over");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.remove("drag-over");
    });
  });
  zone.addEventListener("drop", (event) => {
    uploadResumeFile(event.dataTransfer.files[0]);
  });
}

function init() {
  setStatus("llmStatus", "AI 演示模式", true);
  setStatus("smtpStatus", "SMTP 演示模式", true);
  setStatus("resumeStatus", "简历待选择", false);
  el("generateBtn").addEventListener("click", generateDraft);
  el("sendBtn").addEventListener("click", sendMail);
  el("copyTitleBtn").addEventListener("click", () => copyText("subjectPreview", "标题"));
  el("copyBodyBtn").addEventListener("click", () => copyText("bodyPreview", "正文"));
  el("readClipboardBtn").addEventListener("click", readClipboardAndParse);
  el("parsePasteBtn").addEventListener("click", () =>
    applySmartFields(extractSmartFields(el("smartPasteBox").value)),
  );
  el("sampleBtn").addEventListener("click", fillSample);
  el("smartPasteBox").addEventListener("paste", () => {
    window.setTimeout(() => applySmartFields(extractSmartFields(el("smartPasteBox").value)), 0);
  });
  initResumeUpload();
  fillSample();
}

init();
