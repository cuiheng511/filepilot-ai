#!/usr/bin/env python3
"""Push filepilot-ai to GitHub using token authentication."""

import base64
import json
import os
import subprocess
import urllib.request

REPO_NAME = "filepilot-ai"
GITHUB_USER = "cuiheng511"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DESCRIPTION = "Smart file management tool — AI-powered file scanning, search, deduplication, and auto-categorization"


def github_api(method, url, data=None):
    """Make a GitHub API request."""
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "filepilot-ai-push-script")

    if data is not None:
        data = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")

    try:
        response = urllib.request.urlopen(req, data=data, timeout=30)
        return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"⚠️ API Error ({e.code}): {body}")
        return None


def create_github_repo():
    """Create the GitHub repository."""
    print(f"📦 Creating repository {GITHUB_USER}/{REPO_NAME}...")
    result = github_api(
        "POST",
        "https://api.github.com/user/repos",
        {
            "name": REPO_NAME,
            "description": DESCRIPTION,
            "private": False,
            "auto_init": False,
        },
    )
    if result and "clone_url" in result:
        print(f"✅ Repository created: {result['html_url']}")
        return result["clone_url"]
    elif result and "errors" in result:
        if any("already exists" in e.get("message", "") for e in result["errors"]):
            print("ℹ️ Repository already exists, will push to existing repo")
            return f"https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
    return None


def run_git_command(args, cwd=None):
    """Run a git command."""
    cmd = ["git"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"  ⚠️  {result.stderr.strip()}")
    else:
        print(f"  ✅{result.stdout.strip()[:100] if result.stdout else 'OK'}")
    return result.returncode == 0


def push_to_github():
    """Initialize git and push to GitHub."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    print(f"📂 Working directory: {project_dir}")

    # Check if git is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=10)
    except FileNotFoundError:
        print("⚠️ Git is not installed. Please install Git for Windows:")
        print("   https://git-scm.com/download/win")
        return False

    remote_url = f"https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
    auth_header = "Authorization: Basic " + base64.b64encode(
        f"{GITHUB_USER}:{TOKEN}".encode("ascii")
    ).decode("ascii")

    # Step 1: Initialize git repo
    if os.path.exists(".git"):
        print("ℹ️ Git repo already initialized")
    else:
        print("📦 Initializing git repository...")
        run_git_command(["init"])

    # Step 2: Add all files
    print("📦 Adding files...")
    run_git_command(["add", "."])

    # Step 3: Check if there's anything to commit
    result = subprocess.run(
        ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10
    )
    if not result.stdout.strip():
        print("ℹ️ No changes to commit")
    else:
        print("📦 Committing...")
        run_git_command(["commit", "-m", "🚀 Initial commit: FilePilot AI"])

    # Step 4: Rename branch to main
    print("🌿 Setting branch to main...")
    run_git_command(["branch", "-M", "main"])

    # Step 5: Add remote
    print("🔗 Adding remote origin...")
    run_git_command(["remote", "remove", "origin"])
    run_git_command(["remote", "add", "origin", remote_url])

    # Step 6: Push
    print("🚀 Pushing to GitHub...")
    result = subprocess.run(
        ["git", "-c", f"http.extraHeader={auth_header}", "push", "-u", "origin", "main"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode == 0:
        print("\n✅ SUCCESS! Repository pushed to GitHub!")
        print(f"   https://github.com/{GITHUB_USER}/{REPO_NAME}")
        return True
    else:
        print(f"⚠️ Push failed: {result.stderr}")
        # Try with GCM disabled
        print("🔄 Retrying with basic auth...")
        env = os.environ.copy()
        env["GCM_INTERACTIVE"] = "never"
        result = subprocess.run(
            [
                "git",
                "-c",
                "credential.helper=",
                "-c",
                f"http.extraHeader={auth_header}",
                "push",
                "-u",
                "origin",
                "main",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        if result.returncode == 0:
            print("\n✅ SUCCESS! Repository pushed to GitHub!")
            print(f"   https://github.com/{GITHUB_USER}/{REPO_NAME}")
            return True
        else:
            print(f"⚠️ Push failed again: {result.stderr}")
            return False


if __name__ == "__main__":
    print("=" * 50)
    print("🚀 FilePilot AI - GitHub Publisher")
    print("=" * 50)

    repo_url = create_github_repo()
    if repo_url:
        success = push_to_github()
        if success:
            print("\n🎉 All done! Don't forget to revoke your token!")
        else:
            print("\n⚠️ Push failed. Try running the commands manually.")
            print("   See instructions in README.md")
    else:
        # Try pushing even if repo creation failed (might already exist)
        print("ℹ️ Could not create repo, attempting push anyway...")
        push_to_github()
