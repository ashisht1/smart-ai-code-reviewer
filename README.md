# 🤖 Smart AI Code Reviewer

A **serverless, Git-like AI code review platform** built for the Careem AI Challenge. Paste Python code, set custom coding guidelines, and receive instant deep code reviews powered by **Google Gemini AI** — all running on **AWS Lambda** with zero external dependencies.

🔗 **Live App:** [https://8ftqsyucec.execute-api.us-east-1.amazonaws.com](https://8ftqsyucec.execute-api.us-east-1.amazonaws.com)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🌐 **Serverless Web UI** | Git-like dark-themed interface served directly from AWS Lambda |
| 📊 **AST Static Analysis** | Computes lines, functions, classes, complexity, docstring coverage using Python's `ast` module |
| 🤖 **Gemini AI Review** | Deep semantic review using Google Gemini 2.5 Flash — readability, design, bugs, and actionable fixes |
| 📝 **Custom Guidelines** | Paste any coding standards or team rules for the AI to follow during review |
| ⚡ **Zero Dependencies** | Uses only Python stdlib (`ast`, `urllib`) — no packages needed on Lambda |
| 🚀 **One-Command Deploy** | `deploy_to_aws.py` automates IAM, Lambda, and API Gateway setup end-to-end |

---

## 🏗️ Architecture

```
Developer (Browser)
    │
    ├── GET /          → Returns index.html UI
    └── POST /review   → Runs AST analysis + Gemini API review
          │
    [API Gateway HTTP API]
          │
    [AWS Lambda: smart-code-reviewer]
          ├── Python ast module (static analysis)
          └── Gemini 2.5 Flash REST API (AI review)
```

---

## 📁 Project Structure

```
smart_code_reviewer/
├── lambda_function.py   # AWS Lambda handler (GET UI + POST review)
├── index.html           # Serverless web UI (Git-like dark theme)
├── local_server.py      # Local dev server (mimics Lambda routing)
├── smart_reviewer.py    # CLI reviewer with guidelines.txt support
├── deploy_to_aws.py     # One-command boto3 deployment script
├── guidelines.txt       # Custom coding guidelines template
├── test_sample.py       # Sample code with intentional flaws for testing
├── requirements.txt     # Python dependencies (google-generativeai, rich)
└── README.md            # This file
```

---

## 🚀 Quick Start

### Run Locally (No AWS Required)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Gemini API key (get one free at aistudio.google.com)
export GEMINI_API_KEY="your_key_here"

# 3. Start local server
python3 local_server.py
```
Open **http://localhost:8000** in your browser.

### CLI Mode

```bash
# Review a file with default staff-engineer guidelines
python3 smart_reviewer.py test_sample.py

# Review with custom guidelines
python3 smart_reviewer.py mycode.py my_guidelines.txt
```

### Deploy to AWS Lambda

```bash
# Requires: AWS credentials configured (boto3)
export GEMINI_API_KEY="your_key_here"
python3 deploy_to_aws.py
```
The script will:
1. Create an IAM role with Lambda execution permissions
2. Package and upload `lambda_function.py` + `index.html`
3. Create an **API Gateway HTTP API** and wire it to Lambda
4. Print the live public URL

---

## 📋 Custom Guidelines

Create or edit `guidelines.txt` to define your team's coding standards:

```
Review code as a Staff Software Engineer.
Prioritize:
- Security issues (SQL injection, unsanitized inputs)
- Performance bottlenecks (N+1 queries, unnecessary loops)
- PEP 8 compliance and type hints
- SOLID principles and single-responsibility
```

The AI will use your guidelines as its review persona — leave it empty to use the default staff-engineer template.

---

## 🔧 AWS Resources Created

| Resource | Name |
|---|---|
| Lambda Function | `smart-code-reviewer` |
| IAM Role | `smart-code-reviewer-lambda-role` |
| API Gateway | `smart-code-reviewer-api` |
| Region | `us-east-1` |

---

## 🛡️ Security Notes

- The API is public (no auth). For production, add API Gateway authorization.
- Never commit your `GEMINI_API_KEY` — set it as a Lambda environment variable via AWS Console.
- The Lambda function only reads code strings you explicitly send — no filesystem access.

---

## 🧠 Technical Decisions

### Why `urllib` instead of `google-generativeai` SDK?
AWS Lambda has a **250 MB deployment package limit**. Using pure `urllib` calls to the Gemini REST API keeps the deployment package under **15 KB** with zero packaging complexity.

### Why API Gateway instead of Lambda Function URLs?
Lambda Function URLs return `403 Forbidden` on root AWS accounts due to account-level SCPs. API Gateway HTTP API is universally compatible and adds CORS support.

---

## 📝 License

MIT — built as part of the Careem AI Engineering Challenge.
