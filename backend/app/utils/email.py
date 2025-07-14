from flask import current_app
from flask_mail import Message
from backend.app.extensions import mail

def send_reset_email(recipient_email, reset_url):
    msg = Message('Password Reset Request',
                 recipients=[recipient_email])
    msg.body = f'''To reset your password, visit:
{reset_url}

This link expires in 1 hour.
'''
    current_app.mail.send(msg)

def send_email(subject, recipients, body):
    try:
        msg = Message(subject, recipients=recipients, body=body)
        mail.send(msg)
        current_app.logger.info(f"Email sent to {recipients}")
    except Exception as e:
        current_app.logger.error(f"Email sending failed: {str(e)}")