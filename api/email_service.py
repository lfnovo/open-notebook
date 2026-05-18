"""
Email service for sending verification codes.
Supports SMTP and Resend API backends.
"""

import os
import random
import smtplib
import string
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from loguru import logger

# Email provider: 'smtp', 'resend', or 'debug'
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp").lower()

# Resend API
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# SMTP settings
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@lumina.ai"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

# App name for email templates
APP_NAME = os.getenv("APP_NAME", "Lumina")


def generate_code(length: int = 6) -> str:
    """Generate a random numeric verification code."""
    return "".join(random.choices(string.digits, k=length))


def build_verification_email(code: str, purpose: str, language: str = "en") -> tuple[str, str]:
    """Build the subject and HTML body for a verification email.

    Returns:
        (subject, html_body)
    """
    if purpose in {"register", "profile_email"}:
        if language == "zh-CN":
            subject = (
                f"{APP_NAME} — 邮箱验证码"
                if purpose == "profile_email"
                else f"{APP_NAME} — 注册验证码"
            )
            action_text = "验证您的邮箱" if purpose == "profile_email" else f"注册 {APP_NAME}"
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                <h2 style="color: #6f6559;">{APP_NAME}</h2>
                <p>您好，</p>
                <p>请使用以下验证码{action_text}：</p>
                <div style="background: #f5f0e8; border-radius: 8px; padding: 16px 24px; margin: 24px 0; text-align: center;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #6f6559;">{code}</span>
                </div>
                <p style="color: #888; font-size: 14px;">验证码将在 <strong>10 分钟</strong>后过期，请尽快使用。</p>
                <p style="color: #888; font-size: 14px;">如果您没有发起此操作，请忽略此邮件。</p>
            </body>
            </html>
            """
        else:
            subject = f"{APP_NAME} — Email Verification Code"
            action_text = (
                "verify your email address"
                if purpose == "profile_email"
                else f"sign up for {APP_NAME}"
            )
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                <h2 style="color: #6f6559;">{APP_NAME}</h2>
                <p>Hello,</p>
                <p>Use this code to {action_text}:</p>
                <div style="background: #f5f0e8; border-radius: 8px; padding: 16px 24px; margin: 24px 0; text-align: center;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #6f6559;">{code}</span>
                </div>
                <p style="color: #888; font-size: 14px;">This code expires in <strong>10 minutes</strong>.</p>
                <p style="color: #888; font-size: 14px;">If you didn't request this, please ignore this email.</p>
            </body>
            </html>
            """
    else:  # reset_password
        if language == "zh-CN":
            subject = f"{APP_NAME} — 密码重置验证码"
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                <h2 style="color: #6f6559;">{APP_NAME}</h2>
                <p>您好，</p>
                <p>我们收到了您的密码重置请求。您的验证码是：</p>
                <div style="background: #f5f0e8; border-radius: 8px; padding: 16px 24px; margin: 24px 0; text-align: center;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #6f6559;">{code}</span>
                </div>
                <p style="color: #888; font-size: 14px;">验证码将在 <strong>10 分钟</strong>后过期，请尽快使用。</p>
                <p style="color: #888; font-size: 14px;">如果您没有发起密码重置，请忽略此邮件。</p>
            </body>
            </html>
            """
        else:
            subject = f"{APP_NAME} — Password Reset Code"
            html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                <h2 style="color: #6f6559;">{APP_NAME}</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password. Your verification code is:</p>
                <div style="background: #f5f0e8; border-radius: 8px; padding: 16px 24px; margin: 24px 0; text-align: center;">
                    <span style="font-size: 28px; font-weight: bold; letter-spacing: 8px; color: #6f6559;">{code}</span>
                </div>
                <p style="color: #888; font-size: 14px;">This code expires in <strong>10 minutes</strong>.</p>
                <p style="color: #888; font-size: 14px;">If you didn't request this, please ignore this email.</p>
            </body>
            </html>
            """

    return subject, html


def send_email_smtp(to: str, subject: str, html_body: str) -> bool:
    """Send an email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to

        part = MIMEText(html_body, "html")
        msg.attach(part)

        if SMTP_PORT == 465:
            # SMTPS implicit TLS (common for port 465)
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
            server.ehlo()
        elif SMTP_USE_TLS:
            # SMTP + STARTTLS (common for port 587)
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)

        server.sendmail(SMTP_FROM, [to], msg.as_string())
        server.quit()
        logger.info(f"Email sent via SMTP to {to}")
        return True
    except Exception as e:
        logger.error(f"SMTP email failed to {to}: {e}")
        return False


def send_email_resend(to: str, subject: str, html_body: str) -> bool:
    """Send an email via Resend API."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not set")
        return False

    try:
        import json
        import urllib.request

        data = json.dumps({
            "from": SMTP_FROM,
            "to": [to],
            "subject": subject,
            "html": html_body,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=data,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                logger.info(f"Email sent via Resend to {to}")
                return True
            else:
                logger.error(f"Resend API error: {resp.status} {resp.read().decode()}")
                return False
    except Exception as e:
        logger.error(f"Resend email failed to {to}: {e}")
        return False


def send_verification_email(
    to: str,
    code: str,
    purpose: str,
    language: str = "en",
) -> bool:
    """Send a verification code email to the given address.

    Args:
        to: Recipient email address
        code: 6-digit verification code
        purpose: 'register', 'profile_email', or 'reset_password'
        language: 'en' or 'zh-CN'

    Returns:
        True if sent successfully
    """
    subject, html = build_verification_email(code, purpose, language)

    if EMAIL_PROVIDER == "resend":
        return send_email_resend(to, subject, html)
    elif EMAIL_PROVIDER == "debug":
        logger.warning(
            f"[DEBUG EMAIL] to={to} purpose={purpose} code={code} subject={subject}"
        )
        return True
    else:
        return send_email_smtp(to, subject, html)
