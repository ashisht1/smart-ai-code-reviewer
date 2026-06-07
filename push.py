#!/usr/bin/env python3
"""
push.py - One-command commit, redeploy to AWS Lambda, and push to GitHub.

Usage:
    python3 push.py "your commit message"
    python3 push.py  # uses a default commit message
"""
import sys
import os
import subprocess
import zipfile
import boto3
import time

FUNCTION_NAME = "smart-code-reviewer"
REGION = "us-east-1"

def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"[ERROR] {cmd}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()

def redeploy():
    print("📦 Repackaging Lambda zip...")
    with zipfile.ZipFile("deployment.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write("lambda_function.py")
        z.write("index.html")
    
    client = boto3.client("lambda", region_name=REGION)
    with open("deployment.zip", "rb") as f:
        zip_bytes = f.read()
    
    print("🚀 Deploying to AWS Lambda...")
    client.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
    time.sleep(3)
    print("✅ Lambda deployed.")

def push_to_git(message):
    print("📝 Committing changes to git...")
    run("git add .")
    # Check if there are changes to commit
    status = subprocess.run("git diff --cached --quiet", shell=True)
    if status.returncode == 0:
        print("ℹ️  No changes to commit.")
    else:
        run(f'git commit -m "{message}"')
        print("⬆️  Pushing to GitHub...")
        run("git push origin main")
        print("✅ Pushed to GitHub.")

def main():
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "chore: update smart-ai-code-reviewer"
    
    print(f"\n🤖 Smart AI Code Reviewer — Deploy & Push")
    print(f"📌 Commit message: {message}\n")
    
    redeploy()
    push_to_git(message)
    
    print(f"\n🎉 Done! Live at: https://8ftqsyucec.execute-api.us-east-1.amazonaws.com")
    print(f"📦 GitHub: https://github.com/ashisht1/smart-ai-code-reviewer\n")

if __name__ == "__main__":
    main()
