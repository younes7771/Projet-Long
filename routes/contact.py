from flask import Blueprint, render_template, request, flash, redirect, url_for
from utils.email import send_email
from datetime import datetime

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validation simple
        if not nom or not email or not message:
            flash('Tous les champs sont obligatoires', 'error')
            return redirect(url_for('contact.contact'))
        
        # Envoyer l'email
        subject = f"Message de contact de {nom}"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Nouveau message de contact</h2>
            <p><strong>De:</strong> {nom}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <h3>Message:</h3>
            <p style="background: #f5f5f5; padding: 15px; border-radius: 5px;">{message}</p>
        </body>
        </html>
        """
        
        # Envoyer à l'administrateur (vous pouvez changer l'email)
        admin_email = 'evalyquiz@gmail.com'  # ou votre email
        
        if send_email(admin_email, subject, body):
            flash('Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.', 'success')
        else:
            flash('Une erreur est survenue lors de l\'envoi du message. Veuillez réessayer plus tard.', 'error')
        
        return redirect(url_for('contact.contact'))
    
    return render_template('contact.html')