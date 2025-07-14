from flask import current_app
from flask_mail import Message
from backend.app.extensions import mail

def send_reset_email(recipient_email, reset_url):
    try:
        msg = Message(
            subject='Password Reset Request',
            recipients=[recipient_email],
            body=f'''To reset your password, visit:
{reset_url}

This link expires in 1 hour.
'''
        )
        mail.send(msg)
        current_app.logger.info(f"Password reset email sent to {recipient_email}")
    except Exception as e:
        current_app.logger.error(f"Failed to send reset email to {recipient_email}: {str(e)}")


def send_email(subject, recipients, body):
    try:
        msg = Message(subject=subject, recipients=recipients, body=body)
        mail.send(msg)
        current_app.logger.info(f"Email sent to {recipients}")
    except Exception as e:
        current_app.logger.error(f"Email sending failed to {recipients}: {str(e)}")
