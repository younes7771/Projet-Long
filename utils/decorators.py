from functools import wraps
from flask import session, flash, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

def enseignant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'enseignant':
            flash('Accès refusé')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated

def etudiant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'etudiant':
            flash('Accès refusé')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Accès refusé')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated