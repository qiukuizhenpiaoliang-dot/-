const state = {
  draftReady: false,
  resumeUploading: false,
};

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

function setLoading(button, loading, text) {
  if (!button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  button.disabled = loading;
  button.textContent = loading ? text : button.dataset.label;
}

function setStatus(id, text, ok) {
  const node = el(id);
  node.textContent = text;
  node.classList.remove("ok", "warn");
  node.classList.add(ok ? "ok" : "warn");
}

function linesFromTextarea(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function collectProfile() {
  return {
    name: el("profileName").value,
    school: el("profileSchool").value,
    graduation_year: el("profileYear").value,
    major: el("profileMajor").value,
    target_role: el("targetRole").value,
    availability: el("profileAvailability").value,
    internship_period: el("profilePeriod").value,
    phone: el("profilePhone").value,
    contact_email: el("profileEmail").value,
    summary: el("profileSummary").value,
    highlights: linesFromTextarea(el("profileHighlights").value),
  };
}

function fillProfile(profile, settings) {
  el("profileName").value = profile.name || "";
  el("profileSchool").value = profile.school || "";
  el("profileYear").value = profile.graduation_year || "";
  el("profileMajor").value = profile.major || "";
  el("targetRole").value = profile.target_role || "";
  el("profileAvailability").value = profile.availability || "";
  el("profilePeriod").value = profile.internship_period || "";
  el("profilePhone").value = profile.phone || "";
  el("profileEmail").value = profile.contact_email || settings.sender_email || "";
  el("profileSummary").value = profile.summary || "";
  el("profileHighlights").value = (profile.highlights || []).join("\n");
  el("resumePath").value = settings.resume_path || "";
  if (settings.resume_path) {
    updateResumeDisplay(settings.resume_path);
  }
}

async function requestJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "请求失败");
  }
  return data;
}

async function loadProfile() {
  const response = await fetch("/api/profile");
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "加载配置失败");
  }
  fillProfile(data.profile, data.settings);
  setStatus(
    "llmStatus",
    data.settings.openai_configured
      ? `AI ${data.settings.openai_model}`
      : "AI 本地预览",
    true,
  );
  setStatus("smtpStatus", data.settings.smtp_configured ? "SMTP 已配置" : "SMTP 未配置", data.settings.smtp_configured);
  setStatus("resumeStatus", data.settings.resume_exists ? "简历已就绪" : "简历未就绪", data.settings.resume_exists);
}

async function generateDraft() {
  const button = el("generateBtn");
  setLoading(button, true, "生成中");
  try {
    const data = await requestJson("/api/draft", {
      hr_email: el("hrEmail").value,
      company: el("company").value,
      target_role: el("targetRole").value,
      resume_path: el("resumePath").value,
      jd_text: el("jdText").value,
      profile: collectProfile(),
    });
    const draft = data.draft;
    el("subjectPreview").value = draft.title || "";
    el("bodyPreview").value = draft.body || "";
    state.draftReady = Boolean(draft.title && draft.body);
    el("sendBtn").disabled = !state.draftReady;
    toast(`已生成：${draft.provider}`);
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
  const ok = window.confirm(`确认发送到 ${el("hrEmail").value}？`);
  if (!ok) {
    return;
  }
  const button = el("sendBtn");
  setLoading(button, true, "发送中");
  try {
    const data = await requestJson("/api/send", {
      hr_email: el("hrEmail").value,
      subject: el("subjectPreview").value,
      body: el("bodyPreview").value,
      resume_path: el("resumePath").value,
    });
    toast(`已发送：${data.sent.attachment_name}`);
  } catch (error) {
    toast(error.message);
  } finally {
    setLoading(button, false);
    el("sendBtn").disabled = !state.draftReady;
  }
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
    /((?:\/Users\/|\/|[A-Za-z]:\\)[^\n\r]+\.(?:pdf|docx?|PDF|DOCX?))/i,
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
        if (/^(?:公司|公司名称|企业|单位|部门|邮箱|HR邮箱|接收邮箱|投递邮箱|简历|附件|岗位|职位|应聘岗位|投递岗位|目标岗位)[:：]/i.test(trimmed)) {
          return false;
        }
        return true;
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
  setStatus("resumeStatus", "简历已就绪", true);
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    };
    reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function uploadResumeFile(file) {
  if (!file) return;
  const suffix = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "doc", "docx"].includes(suffix)) {
    toast("简历仅支持 PDF、DOC、DOCX");
    return;
  }
  if (file.size > 25 * 1024 * 1024) {
    toast("简历文件超过 25MB");
    return;
  }

  const zone = el("resumeDropzone");
  state.resumeUploading = true;
  zone.classList.add("loading");
  el("resumeDropTitle").textContent = "上传中";
  el("resumeDropMeta").textContent = file.name;
  try {
    const dataBase64 = await fileToBase64(file);
    const data = await requestJson("/api/upload-resume", {
      filename: file.name,
      content_type: file.type,
      data_base64: dataBase64,
    });
    el("resumePath").value = data.resume.path;
    updateResumeDisplay(data.resume.path);
    toast("简历已上传");
  } catch (error) {
    toast(error.message);
  } finally {
    state.resumeUploading = false;
    zone.classList.remove("loading", "drag-over");
  }
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
    const file = event.dataTransfer.files[0];
    uploadResumeFile(file);
  });
}

el("generateBtn").addEventListener("click", generateDraft);
el("sendBtn").addEventListener("click", sendMail);
el("copyTitleBtn").addEventListener("click", () => copyText("subjectPreview", "标题"));
el("copyBodyBtn").addEventListener("click", () => copyText("bodyPreview", "正文"));
el("readClipboardBtn").addEventListener("click", readClipboardAndParse);
el("parsePasteBtn").addEventListener("click", () =>
  applySmartFields(extractSmartFields(el("smartPasteBox").value)),
);
el("smartPasteBox").addEventListener("paste", () => {
  window.setTimeout(() => applySmartFields(extractSmartFields(el("smartPasteBox").value)), 0);
});

initResumeUpload();
loadProfile().catch((error) => toast(error.message));
