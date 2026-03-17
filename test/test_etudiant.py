import pytest
from models.database import get_db

@pytest.fixture(autouse=True)
def setup_quiz_data(app):
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM reponse_etudiant")
        db.execute("DELETE FROM resultat_quiz")
        db.execute("DELETE FROM choix_reponse")
        db.execute("DELETE FROM question")
        db.execute("DELETE FROM quiz")
        
        db.execute("INSERT INTO quiz (id, titre, status, id_matiere, id_enseignant) VALUES (1, 'Examen Final', 'publié', 1, 1)")
        
        db.execute("INSERT INTO question (id, enonce, type, duree, bareme, id_quiz, id_enseignant) VALUES (1, '2+2?', 'numerique', 60, 2, 1, 1)")
        
        db.execute("INSERT INTO question (id, enonce, type, duree, bareme, id_quiz, id_enseignant) VALUES (2, 'Couleurs drapeau FRANCE?', 'QCM_multiple', 60, 3, 1, 1)")
        db.execute("INSERT INTO choix_reponse (id, id_question, texte, est_correct) VALUES (10, 2, 'Bleu', 1)")
        db.execute("INSERT INTO choix_reponse (id, id_question, texte, est_correct) VALUES (11, 2, 'Rouge', 1)")
        db.execute("INSERT INTO choix_reponse (id, id_question, texte, est_correct) VALUES (12, 2, 'Vert', 0)")
        
        db.commit()

def test_access_quiz_page(auth_etudiant, app):
    """Vérifie l'accès à la page d'un quiz et l'affichage correct de son contenu."""
    response = auth_etudiant.get('/etudiant/quiz/1/take')
    html = response.data.decode('utf-8')
    assert response.status_code == 200
    # On cherche "Examen Final" car c'est le nom défini dans la fixture setup_quiz_data
    assert "Examen Final" in html  
    assert "2+2" in html

def test_submit_quiz_logic(auth_etudiant, app):
    """Vérifie l'enregistrement d'une réponse numérique et le calcul du score."""
    response = auth_etudiant.post('/etudiant/quiz/1/submit', data={
        'question_1': '4'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Score" in response.data
    with app.app_context():
        db = get_db()
        res = db.execute("SELECT * FROM resultat_quiz WHERE id_etudiant = 3 AND id_quiz = 1").fetchone()
        assert res is not None
        rep = db.execute("SELECT * FROM reponse_etudiant WHERE id_resultat = ?", (res['id'],)).fetchone()
        assert rep['texte_reponse'] == '4'

def test_prevent_double_submission(auth_etudiant, app):
    """Vérifie qu'un étudiant ne peut pas passer deux fois le même quiz."""
    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO resultat_quiz (id_quiz, id_etudiant, score) VALUES (1, 3, 20)")
        db.commit()
    response = auth_etudiant.get('/etudiant/quiz/1/take', follow_redirects=True)
    html_content = response.data.decode('utf-8')
    assert "déjà passé" in html_content

def test_no_answer_leak_in_html(auth_etudiant):
    """Vérifie que la réponse '4' n'est pas cachée dans le code HTML"""
    response = auth_etudiant.get('/etudiant/quiz/1/take')
    html = response.data.decode('utf-8')
    assert "reponse_correcte" not in html
    
def test_prevent_access_correction_prematurely(auth_etudiant):
    """Vérifie que l'accès direct aux corrections est bloqué"""
    response = auth_etudiant.get('/etudiant/correction/1', follow_redirects=True)
    assert "Résultat non trouvé" in response.data.decode('utf-8')

def test_automatic_submission_on_violation(auth_etudiant):
    """Vérifie que le serveur accepte une soumission vide"""
    response = auth_etudiant.post('/etudiant/quiz/1/submit', data={}, follow_redirects=True)
    assert response.status_code == 200
    assert "Quiz soumis avec succès" in response.data.decode('utf-8')

def test_final_score_calculation(auth_etudiant, app):
    """Vérifie que le score total est correctement calculé et enregistré."""
    form_data = {
        'question_1': '4',
        'question_2': ['10', '11']
    }
    response = auth_etudiant.post('/etudiant/quiz/1/submit', data=form_data, follow_redirects=True)
    html = response.data.decode('utf-8')
    assert "5.0" in html 
    assert "points" in html
    with app.app_context():
        db = get_db()
        resultat = db.execute("SELECT score FROM resultat_quiz WHERE id_quiz = 1 AND id_etudiant = 3").fetchone()    
        assert float(resultat['score']) == 5.0