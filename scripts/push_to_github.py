#!/usr/bin/env python3
"""Push filepilot-ai to GitHub using token authentication."""
import json
import os
import subprocess
import sys
import urllib.request

REPO_NAME = "filepilot-ai"
GITHUB_USER = "cuiheng511"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DESCRIPTION = "馃殌 鏅鸿兘鏂囦欢绠＄悊宸ュ叿 鈥?鍩轰簬 AI 鐨勬枃浠舵壂鎻忋€佹绱€佸幓閲嶄笌鑷姩褰掔被"


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
        print(f"鉂?API Error ({e.code}): {body}")
        return None


def create_github_repo():
    """Create the GitHub repository."""
    print(f"馃摝 Creating repository {GITHUB_USER}/{REPO_NAME}...")
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
        print(f"鉁?Repository created: {result['html_url']}")
        return result["clone_url"]
    elif result and "errors" in result:
        if any("already exists" in e.get("message", "") for e in result["errors"]):
            print(f"鈿狅笍 Repository already exists, will push to existing repo")
            return f"https://github.com/{GITHUB_USER}/{REPO_NAME}.git"
    return None


def run_git_command(args, cwd=None):
    """Run a git command."""
    cmd = ["git"] + args
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"  鈿狅笍  {result.stderr.strip()}")
    else:
        print(f"  鉁?{result.stdout.strip()[:100] if result.stdout else 'OK'}")
    return result.returncode == 0


def push_to_github():
    """Initialize git and push to GitHub."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    print(f"馃搧 Working directory: {project_dir}")

    # Check if git is available
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=10)
    except FileNotFoundError:
        print("鉂?Git is not installed. Please install Git for Windows:")
        print("   https://git-scm.com/download/win")
        return False

    # Create remote URL with token
    remote_url = (
        f"https://{GITHUB_USER}:{TOKEN}@github.com/{GITHUB_USER}/{REPO_NAME}.git"
    )

    # Step 1: Initialize git repo
    if os.path.exists(".git"):
        print("鈿狅笍 Git repo already initialized")
    else:
        print("馃敡 Initializing git repository...")
        run_git_command(["init"])

    # Step 2: Add all files
    print("馃摑 Adding files...")
    run_git_command(["add", "."])

    # Step 3: Check if there's anything to commit
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, timeout=10
    )
    if not result.stdout.strip():
        print("鈿狅笍 No changes to commit")
    else:
        print("馃捑 Committing...")
        run_git_command(["commit", "-m", "馃帀 Initial commit: FilePilot AI"])

    # Step 4: Rename branch to main
    print("馃尶 Setting branch to main...")
    run_git_command(["branch", "-M", "main"])

    # Step 5: Add remote
    print("馃敆 Adding remote origin...")
    run_git_command(["remote", "remove", "origin"])
    run_git_command(["remote", "add", "origin", remote_url])

    # Step 6: Push
    print("馃殌 Pushing to GitHub...")
    result = subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        print(f"\n鉁?SUCCESS! Repository pushed to GitHub!")
        print(f"   https://github.com/{GITHUB_USER}/{REPO_NAME}")
        return True
    else:
        print(f"鉂?Push failed: {result.stderr}")
        # Try with GCM disabled
        print("馃攧 Retrying with basic auth...")
        env = os.environ.copy()
        env["GCM_INTERACTIVE"] = "never"
        result = subprocess.run(
            ["git", "-c", "credential.helper=", "push", "-u", "origin", "main"],
            capture_output=True, text=True, timeout=120, env=env
        )
        if result.returncode == 0:
            print(f"\n鉁?SUCCESS! Repository pushed to GitHub!")
            print(f"   https://github.com/{GITHUB_USER}/{REPO_NAME}")
            return True
        else:
            print(f"鉂?Push failed again: {result.stderr}")
            return False


if __name__ == "__main__":
    print("=" * 50)
    print("馃殌 FilePilot AI - GitHub Publisher")
    print("=" * 50)

    repo_url = create_github_repo()
    if repo_url:
        success = push_to_github()
        if success:
            print("\n馃帀 All done! Don't forget to revoke your token!")
        else:
            print("\n鉂?Push failed. Try running the commands manually.")
            print("   See instructions in README.md")
    else:
        # Try pushing even if repo creation failed (might already exist)
        print("鈿狅笍 Could not create repo, attempting push anyway...")
        push_to_github()

