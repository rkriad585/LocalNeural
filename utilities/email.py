import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config

logger = logging.getLogger(__name__)


def send_reset_email(to_email: str, reset_url: str) -> bool:
    if not Config.SMTP_USER or not Config.SMTP_PASSWORD:
        logger.warning("SMTP not configured — cannot send email")
        return False

    subject = "LocalNeural — Password Reset"
    body = f"""\
<html>
<body style="background:#050505;color:#e5e5e5;font-family:monospace;padding:40px">
<div style="max-width:480px;margin:0 auto;background:#0a0a0a;border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:32px">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:24px">
<div style="width:12px;height:12px;background:#D71921;border-radius:50%"></div>
<span style="font-size:12px;letter-spacing:2px;color:#9ca3af;text-transform:uppercase">Local<span style="color:#D71921;font-weight:bold">Neural</span></span>
</div>
<h2 style="font-size:16px;font-weight:bold;letter-spacing:1px;text-transform:uppercase">Password Reset</h2>
<p style="font-size:13px;color:#9ca3af;line-height:1.6">You requested a password reset. Click the button below to set a new password. This link expires in 1 hour.</p>
<div style="text-align:center;margin:28px 0">
<a href="{reset_url}" style="display:inline-block;background:#D71921;color:#fff;text-decoration:none;padding:12px 32px;border-radius:999px;font-size:13px;font-weight:bold;letter-spacing:1px">Reset Password</a>
</div>
<p style="font-size:11px;color:#6b7280">If you did not request this, ignore this email.</p>
</div>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = Config.SMTP_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reset email: {e}")
        return False
