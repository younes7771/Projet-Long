import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for
import secrets

def send_email(to_email, subject, body):
    """Envoie un email simple"""
    from config import Config
    
    msg = MIMEMultipart()
    msg['From'] = Config.MAIL_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
        server.starttls()
        server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def generate_token():
    """Génère un token unique"""
    return secrets.token_urlsafe(32)

def send_verification_email(user_email, user_nom, token):
    """Envoie l'email de vérification"""
    from flask import url_for
    from app import app
    
    with app.app_context():
        verify_link = url_for('auth.verify_email', token=token, _external=True)
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Bienvenue {user_nom} !</h2>
            <p>Merci de vous être inscrit sur Quiz App.</p>
            <p>Veuillez confirmer votre adresse email en cliquant sur le lien ci-dessous :</p>
            <p><a href="{verify_link}" style="background: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Confirmer mon email</a></p>
            <p>Ou copiez ce lien : {verify_link}</p>
            <p>Ce lien expirera dans 24 heures.</p>
            <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
        </body>
        </html>
        """
        
        return send_email(user_email, "Quiz App - Confirmation d'email", body)

def send_reset_email(user_email, user_nom, token):
    """Envoie l'email de réinitialisation de mot de passe"""
    from flask import url_for
    from app import app
    
    with app.app_context():
        reset_link = url_for('auth.reset_password_form', token=token, _external=True)
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Bonjour {user_nom},</h2>
            <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
            <p>Cliquez sur le lien ci-dessous pour créer un nouveau mot de passe :</p>
            <p><a href="{reset_link}" style="background: #e74c3c; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Réinitialiser mon mot de passe</a></p>
            <p>Ou copiez ce lien : {reset_link}</p>
            <p>Ce lien expirera dans 1 heure.</p>
            <p>Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
        </body>
        </html>
        """
        
        return send_email(user_email, "Quiz App - Réinitialisation de mot de passe", body)