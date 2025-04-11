import subprocess

def get_git_version():
    try:
        return subprocess.check_output(["git", "describe", "--tags", "--always"]).strip().decode("utf-8")
    except Exception:
        return "unknown"


APP_VERSION = get_git_version()