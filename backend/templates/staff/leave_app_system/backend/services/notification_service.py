from flask_mail import Message
from flask import render_template
from app import mail, app

def send_leave_notification(recipient, subject, template, **kwargs):
    msg = Message(
        subject,
        recipients=[recipient],
        sender=app.config['MAIL_DEFAULT_SENDER']
    )
    msg.body = render_template(f'emails/{template}.txt', **kwargs)
    msg.html = render_template(f'emails/{template}.html', **kwargs)
    mail.send(msg)