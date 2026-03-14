import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for
import secrets
from config import Config

def send_email(to_email, subject, body, html=True):
    """Envoie un email (texte ou HTML)"""
    
    msg = MIMEMultipart('alternative')
    msg['From'] = Config.MAIL_USERNAME
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Version texte pour les clients qui ne supportent pas HTML
    text_body = body.replace('<br>', '\n').replace('</p>', '\n').replace('<h2>', '').replace('</h2>', ': ')
    # Nettoyer les balises HTML
    import re
    text_body = re.sub(r'<[^>]+>', '', text_body)
    
    # Attacher les deux versions
    part1 = MIMEText(text_body, 'plain')
    part2 = MIMEText(body, 'html')
    
    msg.attach(part1)
    msg.attach(part2)
    
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
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background: #3498db; color: white; padding: 12px 25px; 
                          text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Evaly Quiz</h1>
                </div>
                <div class="content">
                    <h2>Bienvenue {user_nom} !</h2>
                    <p>Merci de vous être inscrit sur Evaly Quiz. Pour commencer à utiliser votre compte, veuillez confirmer votre adresse email.</p>
                    <p style="text-align: center;">
                        <a href="{verify_link}" class="button">Confirmer mon email</a>
                    </p>
                    <p>Ou copiez ce lien :<br>
                    <small>{verify_link}</small></p>
                    <p><strong>Ce lien expirera dans 24 heures.</strong></p>
                    <p>Si vous n'avez pas créé de compte sur Evaly Quiz, ignorez simplement cet email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 Evaly Quiz - Tous droits réservés</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return send_email(user_email, "Evaly Quiz - Confirmation d'email", body)

def send_reset_email(user_email, user_nom, token):
    """Envoie l'email de réinitialisation de mot de passe"""
    from flask import url_for
    from app import app
    
    with app.app_context():
        reset_link = url_for('auth.reset_password_form', token=token, _external=True)
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; background: #e74c3c; color: white; padding: 12px 25px; 
                          text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #777; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Evaly Quiz</h1>
                </div>
                <div class="content">
                    <h2>Bonjour {user_nom},</h2>
                    <p>Nous avons reçu une demande de réinitialisation de mot de passe pour votre compte Evaly Quiz.</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Réinitialiser mon mot de passe</a>
                    </p>
                    <p>Ou copiez ce lien :<br>
                    <small>{reset_link}</small></p>
                    <p><strong>Ce lien expirera dans 1 heure.</strong></p>
                    <p>Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email en toute sécurité.</p>
                </div>
                <div class="footer">
                    <p>© 2024 Evaly Quiz - Tous droits réservés</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return send_email(user_email, "Evaly Quiz - Réinitialisation de mot de passe", body)