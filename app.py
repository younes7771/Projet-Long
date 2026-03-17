from flask import Flask, redirect, render_template, url_for
from config import Config
from models.database import init_db, close_db
from routes.auth import auth_bp
from routes.enseignant import enseignant_bp
from routes.etudiant import etudiant_bp
from routes.admin import admin_bp
from routes.contact import contact_bp  # NOUVEAU


app = Flask(__name__)
app.config.from_object(Config)

# Initialisation de la base de données uniquement hors tests
# Cela évite les erreurs "UNIQUE constraint failed" lors du setup de pytest
with app.app_context():
    if not app.config.get('TESTING'):
        init_db()
# Initialisation de la base de données


# Créer des données initiales (à supprimer en production)
# try:
#     from init_data import create_initial_data
#     create_initial_data()
# except Exception as e:
#     print(f"Note: Les données initiales n'ont pas pu être créées: {e}")

# Enregistrement des blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(enseignant_bp, url_prefix='/enseignant')
app.register_blueprint(etudiant_bp, url_prefix='/etudiant')
app.register_blueprint(contact_bp)  

# Routes principales
# @app.route('/')
# def index():
#     return redirect(url_for('auth.login'))


@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/home')
def home():
    """Alias pour la page d'accueil"""
    return redirect(url_for('index'))

@app.route('/demo')
def demo():
    return render_template('demo.html')

@app.route('/dashboard')
def dashboard():
    from flask import session
    if session.get('role') == 'enseignant':
        return redirect(url_for('enseignant.dashboard'))
    elif session.get('role') == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('etudiant.dashboard'))

# Gestion de la fermeture de la base de données
app.teardown_appcontext(close_db)

if __name__ == '__main__':
    app.run(debug=True)