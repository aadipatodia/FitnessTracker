import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings
from app.logging_setup import logger


def is_email_configured() -> bool:
    return bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


def send_password_reset_email(to_email: str, reset_link: str) -> bool:
    if not is_email_configured():
        logger.warning("SMTP not configured — cannot send password reset email to %s", to_email)
        return False

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your FitAI password"
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
    msg["To"] = to_email

    text = (
        "We received a request to reset your FitAI password.\n\n"
        f"Reset it here: {reset_link}\n\n"
        "This link expires in 1 hour. If you didn't request this, you can ignore this email."
    )
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2>Reset your FitAI password</h2>
      <p>We received a request to reset your FitAI password.</p>
      <p><a href="{reset_link}" style="display:inline-block;padding:10px 20px;background:#111;color:#fff;
         text-decoration:none;border-radius:6px;">Reset password</a></p>
      <p>Or copy this link: <br>{reset_link}</p>
      <p style="color:#666;font-size:13px;">This link expires in 1 hour. If you didn't request this,
      you can safely ignore this email.</p>
    </div>
    """
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        return False
