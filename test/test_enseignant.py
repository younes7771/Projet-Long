import pytest
from models.database import get_db

@pytest.fixture(autouse=True)
def setup_base_data(app):
    """Prépare la base de données avant CHAQUE test."""
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO matiere (id, nom, id_enseignant) VALUES (1, 'Maths', 1)")
        db.execute("INSERT OR IGNORE INTO quiz (id, titre, id_enseignant, id_matiere) VALUES (1, 'Quiz Test', 1, 1)")
        db.commit()

def test_edit_quiz(auth_prof, app):
    """Vérifie l'ajout d'une question à un quiz via l'action 'add_question'."""
    response = auth_prof.post('/enseignant/quiz/1/edit', data={
        'action': 'add_question',
        'enonce': 'Nouvelle Question',
        'type': 'numerique',
        'bareme': 2,
        'duree_question': 60,
        'bonne_reponse_num': '42'
    }, follow_redirects=True)

    assert b"Question ajout" in response.data
    with app.app_context():
        db = get_db()
        q = db.execute("SELECT * FROM question WHERE id_quiz = 1 ORDER BY id DESC").fetchone()
        assert q['enonce'] == 'Nouvelle Question'

def test_delete_question(auth_prof, app):
    """Vérifie qu'un enseignant peut supprimer l'une de ses propres questions."""
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO question (id, enonce, type, id_quiz, id_enseignant) VALUES (10, 'A supprimer', 'numerique', 1, 1)")
        db.commit()

    auth_prof.get('/enseignant/question/10/delete', follow_redirects=True)

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT * FROM question WHERE id = 10").fetchone() is None

def test_qcm_simple_invalid_answers(auth_prof, app):
    """Vérifie que le système bloque l'ajout d'un QCM simple ayant plus d'une réponse correcte."""
    response = auth_prof.post('/enseignant/quiz/1/edit', data={
        'action': 'add_question',
        'enonce': 'Erreur test',
        'type': 'QCM_simple',
        'bareme': 1,
        'choix[]': ['R1', 'R2'],
        'correct[]': ['0', '1']
    }, follow_redirects=True)

    assert "seule bonne reponse".encode('utf-8') in response.data

def test_isolation_delete(client, app):
    """Vérifie qu'un enseignant ne peut PAS supprimer la question d'un autre enseignant (Sécurité)."""
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO question (id, enonce, type, id_quiz, id_enseignant) VALUES (99, 'Test', 'numerique', 1, 1)")
        db.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['role'] = 'enseignant'

    client.get('/enseignant/question/99/delete')

    with app.app_context():
        db = get_db()
        assert db.execute("SELECT * FROM question WHERE id = 99").fetchone() is not None

def test_edit_question_content(auth_prof, app):
    """Vérifie la modification du contenu (énoncé, barème) d'une question existante."""
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO question (id, enonce, type, bareme, duree, id_quiz, id_enseignant) VALUES (5, 'Ancien Enonce', 'numerique', 1, 60, 1, 1)")
        db.commit()

    response = auth_prof.post('/enseignant/question/5/edit', data={
        'enonce': 'Nouvel Enonce',
        'bareme': 5,
        'duree': 120,
        'reponse_correcte': '10'
    }, follow_redirects=True)

    assert b"modifi" in response.data.lower()
    with app.app_context():
        db = get_db()
        q = db.execute("SELECT * FROM question WHERE id = 5").fetchone()
        assert q['enonce'] == 'Nouvel Enonce'