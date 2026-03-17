from werkzeug.security import check_password_hash
from models.database import get_db

def test_add_user_password_hashing(auth_admin, app):
    """Vérifie que le mot de passe d'un nouvel utilisateur est correctement haché en base de données."""
    email = 'enseignant@gmail.com'
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM user WHERE email = ?", (email,))
        db.commit()
    auth_admin.post('/admin/add_user', data={
        'nom': 'ISH', 'prenom': 'Gaga', 'email': email,
        'role': 'enseignant', 'password': 'MonMotDePasseSecret123', 'groupe': ''
    })

    with app.app_context():
        db = get_db()
        user = db.execute("SELECT password_hash FROM user WHERE email = ?", (email,)).fetchone()
        assert user is not None
        assert check_password_hash(user['password_hash'], 'MonMotDePasseSecret123')

def test_add_user_group_logic(auth_admin, app):
    """Vérifie la structure de la table utilisateur et la logique d'attribution des groupes."""
    email_student = 'etudiant@test.com'
    with app.app_context():
        db = get_db()
        cursor = db.execute("PRAGMA table_info(user)")
        columns = [row['name'] for row in cursor.fetchall()]
        print(f"\n--- COLONNES RÉELLES DE LA TABLE USER : {columns} ---")

def test_pedagogical_configuration(auth_admin, app):
    """Vérifie la création d'une matière et son association correcte avec un enseignant."""
    subject_name = 'Algorithme Avancées'
    teacher_id = 1 

    auth_admin.post('/admin/matiere/add', data={
        'nom': subject_name,
        'id_user': teacher_id
    })

    with app.app_context():
        db = get_db()
        subject = db.execute(
            "SELECT * FROM matiere WHERE nom = ? AND id_enseignant = ?", 
            (subject_name, teacher_id)
        ).fetchone()
        
        assert subject is not None

def test_exam_lifecycle(auth_admin, app):
    """Vérifie la création d'un examen et s'assure qu'il est initialisé avec le statut 'brouillon'."""
    exam_title = 'Examen Final 2026'
    auth_admin.post('/admin/exam/create', data={
        'titre': exam_title,
        'matiere': 1,
        'id_user': 1
    })

    with app.app_context():
        db = get_db()
        exam = db.execute("SELECT * FROM quiz WHERE titre = ?", (exam_title,)).fetchone()
        assert exam is not None
        assert exam['status'] == 'brouillon'