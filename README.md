# 智能求职投递助手

一个本地运行的求职投递工具：粘贴 JD 和 HR 邮箱后，系统会结合你的预设背景生成高度定制的邮件标题与正文，并在确认后通过 SMTP 发送本地简历附件。

项目提交表可查看：[项目简介.md](./项目简介.md)

在线演示：[https://qiukuizhenpiaoliang-dot.github.io/-/](https://qiukuizhenpiaoliang-dot.github.io/-/)

## 功能

- JD 与个人背景匹配分析
- 整段粘贴后自动拆分 HR 邮箱、公司、岗位、简历路径和 JD
- 支持拖拽或点击上传 PDF、DOC、DOCX 简历
- 自动生成投递标题：学校、届别、专业、岗位、到岗时间、实习周期
- 自动生成“总-分-总”结构邮件正文
- 发送前可编辑标题和正文
- SMTP 附件发送，不改动简历原件
- 未配置 OpenAI API key 时提供本地预览生成

## 快速开始

```bash
cd 智能求职投递助手
cp .env.example .env
cp config/profile.example.json config/profile.json
python3 app.py --port 8765
```

然后打开：

```text
http://127.0.0.1:8765
```

## 配置

编辑 `.env`：

```bash
OPENAI_API_KEY=你的 OpenAI API key
OPENAI_BASE_URL=https://lanyiapi.com/v1
OPENAI_MODEL=gpt-5.4-mini
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USERNAME=你的邮箱账号
SMTP_PASSWORD=邮箱授权码或应用密码
SENDER_EMAIL=你的发件邮箱
SENDER_NAME=你的姓名
RESUME_PATH=/你的/简历.pdf
```

编辑 `config/profile.json`，填写学校、届别、专业、到岗时间、实习周期、项目经历等背景信息。生成阶段只会引用这里和页面输入里的信息，不会修改简历文件。

## 发送流程

1. 在页面整段粘贴职位信息，或手动填写 HR 邮箱、公司、岗位、JD 和个人背景。
2. 拖拽或点击上传简历，也可以直接填写简历路径。
3. 点击“生成邮件”，检查标题和正文。
4. 必要时直接编辑标题或正文。
5. 点击“发送邮件”，确认后通过 SMTP 发送简历附件。

## 本地预览模式

如果没有配置 `OPENAI_API_KEY`，系统会使用本地规则生成一版可预览邮件，方便先调通 UI 和 SMTP 设置。配置 API key 并安装 `openai` SDK 后，会自动切换到大模型生成。

```bash
python3 -m pip install -r requirements.txt
```

## 测试

```bash
python3 -m unittest discover -s tests
```

## 部署到 GitHub

先在 GitHub 创建一个空仓库，然后运行：

```bash
scripts/deploy_github.sh git@github.com:你的账号/你的仓库.git
```

如果使用 HTTPS 地址，也可以：

```bash
scripts/deploy_github.sh https://github.com/你的账号/你的仓库.git
```
