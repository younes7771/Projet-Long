from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import get_db
from utils.decorators import login_required
from utils.email import generate_token, send_verification_email, send_reset_email
from datetime import datetime, timedelta
import sqlite3

auth_bp = Blueprint('auth', __name__)

def row_to_dict(row):
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

# ================ INSCRIPTION AVEC VÉRIFICATION EMAIL ================
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        prenom = request.form['prenom']
        email = request.form['email']
        password = request.form['password']
        role_type = request.form['role']
        id_groupe = request.form.get('groupe')
        
        if role_type == 'etudiant' and not id_groupe:
            flash('Veuillez sélectionner un groupe pour les étudiants')
            return redirect(url_for('auth.register'))
        
        db = get_db()
        c = db.cursor()
        c.execute("SELECT id FROM role WHERE user_role = ?", (role_type,))
        role = c.fetchone()
        
        # Générer token de vérification
        verification_token = generate_token()
        
        try:
            if role_type == 'enseignant':
                c.execute('''
                    INSERT INTO user (nom, prenom, email, password_hash, id_role, email_verified, email_verification_token) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (nom, prenom, email, generate_password_hash(password), role[0], 0, verification_token))
            else:
                c.execute('''
                    INSERT INTO user (nom, prenom, email, password_hash, id_role, id_groupe, email_verified, email_verification_token) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (nom, prenom, email, generate_password_hash(password), role[0], id_groupe, 0, verification_token))
            
            db.commit()
            
            # Envoyer email de vérification
            send_verification_email(email, prenom, verification_token)
            
            flash('Inscription réussie! Un email de confirmation vous a été envoyé.')
            return redirect(url_for('auth.login'))
            
        except sqlite3.IntegrityError:
            flash('Email déjà utilisé')
        finally:
            db.close()
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM groupe")
    groupes = [row_to_dict(row) for row in c.fetchall()]
    db.close()
    
    return render_template('auth/register.html', groupes=groupes)

# ================ VÉRIFICATION EMAIL ================
@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    db = get_db()
    c = db.cursor()
    
    c.execute('SELECT * FROM user WHERE email_verification_token = ?', (token,))
    user = c.fetchone()
    
    if not user:
        flash('Lien de vérification invalide ou expiré')
        return redirect(url_for('auth.login'))
    
    # Vérifier si le token n'est pas trop vieux (24h)
    # Optionnel : stocker date_expiration
    
    c.execute('UPDATE user SET email_verified = 1, email_verification_token = NULL WHERE id = ?', (user['id'],))
    db.commit()
    db.close()
    
    flash('Email vérifié avec succès! Vous pouvez maintenant vous connecter.')
    return redirect(url_for('auth.login'))

# ================ CONNEXION AVEC VÉRIFICATION ================
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        db.row_factory = sqlite3.Row
        c = db.cursor()
        c.execute('''
            SELECT u.*, r.user_role, g.nom as groupe_nom, g.id as groupe_id 
            FROM user u 
            JOIN role r ON u.id_role = r.id 
            LEFT JOIN groupe g ON u.id_groupe = g.id 
            WHERE u.email = ?
        ''', (email,))
        user_row = c.fetchone()
        db.close()
        
        if user_row:
            user = row_to_dict(user_row)
            
            # Vérifier si l'email est vérifié
            if not user.get('email_verified', 1):  # 1 pour backward compatibility
                flash('Veuillez vérifier votre email avant de vous connecter')
                return render_template('auth/login.html')
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['nom'] = user['nom']
                session['prenom'] = user['prenom']
                session['role'] = user['user_role']
                session['groupe'] = user['groupe_nom']
                session['id_groupe'] = user['groupe_id']
                return redirect(url_for('dashboard'))
        
        flash('Email ou mot de passe incorrect')
    
    return render_template('auth/login.html')



@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# ================== PROFILE ==================
@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    c = db.cursor()
    user_id = session.get('user_id')

    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        date_naissance = request.form.get('date_naissance', '').strip()

        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        c.execute("SELECT * FROM user WHERE id = ?", (user_id,))
        user = c.fetchone()

        if not user:
            flash("Utilisateur introuvable.")
            return redirect(url_for('auth.login'))

        if not nom or not prenom:
            flash("Le nom et le prénom sont obligatoires.")
            return redirect(url_for('auth.profile'))

        if not current_password and not new_password and not confirm_password:
            c.execute("""
                UPDATE user
                SET nom = ?, prenom = ?, date_naissance = ?
                WHERE id = ?
            """, (
                nom,
                prenom,
                date_naissance if date_naissance else None,
                user_id
            ))
            db.commit()

            session['nom'] = nom
            session['prenom'] = prenom

            flash("Profil mis à jour.")
            return redirect(url_for('auth.profile'))

        if not check_password_hash(user['password_hash'], current_password):
            flash("Mot de passe actuel incorrect.")
            return redirect(url_for('auth.profile'))

        if new_password != confirm_password:
            flash("Les nouveaux mots de passe ne correspondent pas.")
            return redirect(url_for('auth.profile'))

        hashed = generate_password_hash(new_password)

        c.execute("""
            UPDATE user
            SET nom = ?, prenom = ?, date_naissance = ?, password_hash = ?
            WHERE id = ?
        """, (
            nom,
            prenom,
            date_naissance if date_naissance else None,
            hashed,
            user_id
        ))

        db.commit()

        session['nom'] = nom
        session['prenom'] = prenom

        flash("Profil et mot de passe mis à jour.")
        return redirect(url_for('auth.profile'))

    c.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user = c.fetchone()

    return render_template('auth/profile.html', user=user)

# ================ MOT DE PASSE OUBLIÉ ================
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        db = get_db()
        c = db.cursor()
        c.execute('SELECT * FROM user WHERE email = ?', (email,))
        user = c.fetchone()
        
        if user:
            # Générer token de réinitialisation (valable 1h)
            reset_token = generate_token()
            expiry = datetime.now() + timedelta(hours=1)
            
            c.execute('''
                UPDATE user 
                SET reset_password_token = ?, reset_token_expiry = ? 
                WHERE id = ?
            ''', (reset_token, expiry, user['id']))
            db.commit()
            
            # Envoyer email
            send_reset_email(email, user['prenom'], reset_token)
        
        db.close()
        
        # Toujours dire "email envoyé" pour sécurité (évite de révéler si email existe)
        flash('Si cet email existe, un lien de réinitialisation vous a été envoyé.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

# ================ RÉINITIALISATION MOT DE PASSE ================
@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_form(token):
    db = get_db()
    c = db.cursor()
    
    # Vérifier token
    c.execute('''
        SELECT * FROM user 
        WHERE reset_password_token = ? AND reset_token_expiry > ?
    ''', (token, datetime.now()))
    
    user = c.fetchone()
    
    if not user:
        flash('Lien de réinitialisation invalide ou expiré')
        db.close()
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Les mots de passe ne correspondent pas')
            return render_template('auth/reset_password.html', token=token)
        
        # Mettre à jour le mot de passe
        c.execute('''
            UPDATE user 
            SET password_hash = ?, reset_password_token = NULL, reset_token_expiry = NULL 
            WHERE id = ?
        ''', (generate_password_hash(new_password), user['id']))
        db.commit()
        db.close()
        
        flash('Mot de passe mis à jour avec succès! Vous pouvez maintenant vous connecter.')
        return redirect(url_for('auth.login'))
    
    db.close()
    return render_template('auth/reset_password.html', token=token)