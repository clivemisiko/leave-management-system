from flask import current_app
from flask_mail import Message

def send_reset_email(recipient_email, reset_url):
    msg = Message('Password Reset Request',
                 recipients=[recipient_email])
    msg.body = f'''To reset your password, visit:
{reset_url}

This link expires in 1 hour.
'''
    current_app.mail.send(msg)