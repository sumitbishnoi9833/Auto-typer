import os
import time
from datetime import datetime

# =========================
# SETTINGS
# =========================

REPO_URL = "https://github.com/sumit989bishnoi-crypto/auto-ai-.git"
BRANCH = "main"
COMMIT_INTERVAL = 600  # 10 minutes

# =========================
# FIRST TIME SETUP
# =========================

if not os.path.exists(".git"):
    print("[*] Initializing Git Repository...")

    os.system("git init")

    with open("README.md", "a") as f:
        f.write("# auto-ai-\n")

    os.system("git add README.md")
    os.system('git commit -m "first commit"')

    os.system(f"git branch -M {BRANCH}")

    os.system(f"git remote add origin {REPO_URL}")

    os.system(f"git push -u origin {BRANCH}")

# =========================
# AUTO COMMIT LOOP
# =========================

print("[+] Auto Push Started...")

while True:
    try:
        # Add all files
        os.system("git add .")

        # Commit with time
        commit_message = f'Auto Commit {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

        os.system(f'git commit -m "{commit_message}"')

        # Push changes
        os.system(f"git push origin {BRANCH}")

        print(f"[+] Pushed at {datetime.now()}")

    except Exception as e:
        print("[!] Error:", e)

    time.sleep(COMMIT_INTERVAL)