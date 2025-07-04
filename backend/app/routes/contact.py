# routes/contact_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_mail import Message
from ..extensions import mail

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Basic validation
        if not all([name, email, subject, message]):
            flash('All fields are required!', 'danger')
        else:
            try:
                # Send email
                msg = Message(
                    subject=f"MICDE Contact Form: {subject}",
                    sender=email,
                    recipients=['clivebillzerean@gmail.com'],  # Replace with actual email
                    body=f"From: {name} <{email}>\n\n{message}"
                )
                mail.send(msg)
                
                flash('Your message has been sent successfully!', 'success')
                return redirect(url_for('contact.contact'))
            except Exception as e:
                flash(f'Error sending message: {str(e)}', 'danger')
    
    return render_template('contact.html')