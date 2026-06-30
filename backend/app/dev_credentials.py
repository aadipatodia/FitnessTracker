from datetime import datetime
from pathlib import Path

CREDENTIALS_FILE = Path(__file__).resolve().parent.parent / "dev_credentials.txt"


def log_dev_credential(email: str, password: str, full_name: str) -> None:
    """Append plain-text credentials to a local dev file (never use in production)."""
    header = (
        "# Local dev credentials — DO NOT commit or use in production\n"
        "# Passwords are stored here in plain text for your convenience during development.\n\n"
    )
    line = f"{email} | {password} | {full_name}  # registered {datetime.now().isoformat(timespec='seconds')}\n"
    if not CREDENTIALS_FILE.exists():
        CREDENTIALS_FILE.write_text(header + line)
    else:
        with CREDENTIALS_FILE.open("a") as f:
            f.write(line)
