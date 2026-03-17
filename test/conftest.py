import pytest
import os
import tempfile
from app import app as flask_app
from models.database import init_db, get_db

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-key'
    })

    with flask_app.app_context():
        db = get_db()
        with open('schema_test.sql', 'r') as f:
            db.executescript(f.read())
        
        db.execute("INSERT OR IGNORE INTO role (id, user_role) VALUES (1, 'admin')")
        db.execute("INSERT OR IGNORE INTO role (id, user_role) VALUES (2, 'enseignant')")
        db.execute("INSERT OR IGNORE INTO role (id, user_role) VALUES (3, 'etudiant')")
        
        db.execute("INSERT OR IGNORE INTO groupe (id, nom) VALUES (1, 'Groupe 1')")
        
        # Données initiales pour les sessions de test
        db.execute("INSERT OR IGNORE INTO user (id, nom, prenom, email, id_role, password_hash) VALUES (1, 'Prof', 'Test', 'prof@test.com', 2, 'hash')")
        
        db.commit() 
    
    yield flask_app


    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_prof(client):
    """Simule la session d'un enseignant (ID 1)"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'enseignant'
    return client

@pytest.fixture
def auth_etudiant(client):
    """Simule la session d'un étudiant (ID 3, Groupe 1)"""
    with client.session_transaction() as sess:
        sess['user_id'] = 3
        sess['role'] = 'etudiant'
        sess['id_groupe'] = 1
        sess['nom'] = 'Graciella'
    return client

@pytest.fixture
def auth_admin(client):
    """Simule une session admin connectée"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['role'] = 'admin'
    return client