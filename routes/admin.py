from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models.database import get_db
from utils.decorators import login_required, admin_required
from werkzeug.security import generate_password_hash
from datetime import datetime
import csv
import io

admin_bp = Blueprint('admin', __name__)


def row_to_dict(row):
    """Convertit un objet Row en dictionnaire"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}



@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Tableau de bord administrateur"""
    return render_template('admin/admin.html')


@admin_bp.route('/gestion_users')
@admin_required
def gestion_users():
    """
    Gestion des utilisateurs.
    """
    db = get_db()
    users = db.execute('''
        SELECT 
            u.id,
            u.nom, 
            u.prenom, 
            u.email, 
            r.user_role AS role, 
            u.date_creation
        FROM user u
        JOIN role r ON u.id_role = r.id
    ''').fetchall()

    users_list = []
    for row in users:
        user = dict(row)

        # ✅ Conversion de la date pour que strftime fonctionne dans le template
        if user["date_creation"]:
            try:
                # Cas avec microsecondes
                user["date_creation"] = datetime.strptime(user["date_creation"], "%Y-%m-%d %H:%M:%S.%f")
            except ValueError:
                # Cas sans microsecondes
                user["date_creation"] = datetime.strptime(user["date_creation"], "%Y-%m-%d %H:%M:%S")

        users_list.append(user)

    return render_template('admin/gestion_users.html', users=users_list)

@admin_bp.route('/add_user', methods=['POST'])
@admin_required
def add_user():
    db = get_db()

    # 🔹 Récupération des champs du formulaire
    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    email = request.form.get('email')
    role_name = request.form.get('role')
    password = request.form.get('password')
    id_groupe = request.form.get('id_groupe')  # récupère le groupe choisi

    # 🔹 Vérification des champs obligatoires
    if not nom or not prenom or not email or not role_name or not password:
        flash("Tous les champs obligatoires doivent être remplis.", "danger")
        return redirect(url_for('admin.gestion_users'))

    # 🔹 Récupération de l'id du rôle
    role_row = db.execute(
        "SELECT id FROM role WHERE user_role = ?",
        (role_name,)
    ).fetchone()

    if not role_row:
        flash("Rôle invalide.", "danger")
        return redirect(url_for('admin.gestion_users'))

    role_id = role_row["id"]

    # 🔹 Vérification de l'id du groupe (optionnel)
    if id_groupe:
        try:
            id_groupe = int(id_groupe)
        except ValueError:
            flash("Groupe invalide.", "danger")
            return redirect(url_for('admin.gestion_users'))

        groupe_row = db.execute(
            "SELECT id FROM groupe WHERE id = ?",
            (id_groupe,)
        ).fetchone()
        if not groupe_row:
            flash("Groupe invalide.", "danger")
            return redirect(url_for('admin.gestion_users'))
    else:
        id_groupe = None  # aucun groupe sélectionné

    # 🔹 Hashage sécurisé du mot de passe
    hashed_password = generate_password_hash(password)

    # 🔹 Insertion dans la base
    db.execute(
        """
        INSERT INTO user (nom, prenom, email, password_hash, id_role, id_groupe, date_creation)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (nom, prenom, email, hashed_password, role_id, id_groupe, datetime.now())
    )
    db.commit()

    flash("Utilisateur ajouté avec succès ✅", "success")
    return redirect(url_for('admin.gestion_users'))



@admin_bp.route('/edit_user', methods=['POST'])
@admin_required
def edit_user():
    db = get_db()

    # Récupération de l'ID depuis le formulaire
    user_id = request.form.get('user_id')

    if not user_id:
        flash("ID utilisateur manquant.", "danger")
        return redirect(url_for('admin.gestion_users'))

    nom = request.form.get('nom')
    prenom = request.form.get('prenom')
    email = request.form.get('email')
    role_name = request.form.get('role')
    password = request.form.get('password')

    # Vérification des champs obligatoires (sauf mot de passe)
    if not nom or not prenom or not email or not role_name:
        flash("Tous les champs sont obligatoires.", "danger")
        return redirect(url_for('admin.gestion_users'))

    # Récupération de l'id du rôle
    role_row = db.execute(
        "SELECT id FROM role WHERE user_role = ?",
        (role_name,)
    ).fetchone()

    if not role_row:
        flash("Rôle invalide.", "danger")
        return redirect(url_for('admin.gestion_users'))

    role_id = role_row["id"]

    # Mise à jour selon que le mot de passe est rempli ou non
    if password:
        hashed_password = generate_password_hash(password)
        db.execute(
            "UPDATE user SET nom = ?, prenom = ?, email = ?, password_hash = ?, id_role = ? WHERE id = ?",
            (nom, prenom, email, hashed_password, role_id, user_id)
        )
    else:
        db.execute(
            "UPDATE user SET nom = ?, prenom = ?, email = ?, id_role = ? WHERE id = ?",
            (nom, prenom, email, role_id, user_id)
        )

    db.commit()
    flash("Utilisateur modifié avec succès ✅", "success")
    return redirect(url_for('admin.gestion_users'))

@admin_bp.route('/delete_user', methods=['POST'])
@admin_required
def delete_user():
    """
    Supprime un utilisateur à partir de son ID.
    """
    db = get_db()

    # Récupération de l'ID utilisateur depuis le formulaire POST
    user_id = request.form.get('user_id')

    if not user_id:
        flash("ID utilisateur manquant.", "danger")
        return redirect(url_for('admin.gestion_users'))

    # Vérification que l'utilisateur existe
    user = db.execute(
        "SELECT * FROM user WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for('admin.gestion_users'))

    # Suppression de l'utilisateur
    db.execute("DELETE FROM user WHERE id = ?", (user_id,))
    db.commit()

    flash("Utilisateur supprimé avec succès ✅", "success")
    return redirect(url_for('admin.gestion_users'))


@admin_bp.route('/gestion_examens')
@login_required
@admin_required
def gestion_examens():
    db = get_db()
    c = db.cursor()

    # ✅ Matières (sans toucher à ta logique)
    c.execute("SELECT * FROM matiere")
    matieres = [row_to_dict(row) for row in c.fetchall()]

    # ✅ Groupes
    c.execute("SELECT * FROM groupe")
    groupes = [row_to_dict(row) for row in c.fetchall()]

    # ✅ Examens
    c.execute("SELECT * FROM quiz")
    exams = [row_to_dict(row) for row in c.fetchall()]

    # ✅ TOUS les enseignants présents dans le site
    c.execute("""
        SELECT user.id, user.nom, user.prenom, user.email
        FROM user
        JOIN role ON user.id_role = role.id
        WHERE role.user_role = 'enseignant'
    """)
    enseignants = [row_to_dict(row) for row in c.fetchall()]

    db.close()

    return render_template(
        "admin/gestion_exam.html",
        matieres=matieres,
        groupes=groupes,
        exams=exams,
        enseignants=enseignants  # ✅ liste complète des enseignants
    )


@admin_bp.route('/matiere/add', methods=['POST'])
@login_required
@admin_required
def add_matiere():
    nom = request.form['nom']
    id_enseignant = request.form['id_user']  # vient du <select>

    db = get_db()
    c = db.cursor()

    # ✅ Colonnes EXACTES de ta table
    c.execute(
        "INSERT INTO matiere (id_enseignant, nom) VALUES (?, ?)",
        (id_enseignant, nom)
    )

    # ✅ Récupération automatique de l'id de la matière
    id_matiere = c.lastrowid

    db.commit()
    db.close()

    flash(f"Matière ajoutée avec succès (ID = {id_matiere})")
    return redirect(url_for('admin.gestion_examens'))

@admin_bp.route('/matiere/edit/<int:matiere_id>', methods=['POST'])
@login_required
@admin_required
def edit_matiere(matiere_id):
    db = get_db()
    c = db.cursor()

    # Récupération des champs envoyés par le formulaire inline
    nom = request.form.get("nom")
    id_enseignant = request.form.get("id_enseignant")

    # Validation simple
    if not nom or not id_enseignant:
        flash("Erreur : tous les champs sont requis.", "error")
        return redirect(url_for('admin.gestion_examens'))

    # Mise à jour de la matière dans la base de données
    c.execute("""
        UPDATE matiere
        SET nom = ?, id_enseignant = ?
        WHERE id = ?
    """, (nom, id_enseignant, matiere_id))

    db.commit()
    db.close()

    flash("Matière modifiée avec succès.", "success")
    return redirect(url_for('admin.gestion_examens'))


@admin_bp.route('/matiere/delete/<int:matiere_id>', methods=['POST'])
@login_required
@admin_required
def delete_matiere(matiere_id):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM matiere WHERE id=?", (matiere_id,))
    db.commit()
    db.close()
    flash("Matière supprimée")
    return redirect(url_for('admin.gestion_examens'))


@admin_bp.route('/groupe/add', methods=['POST'])
@login_required
@admin_required
def add_groupe():
    nom = request.form['nom']
    id_enseignant = request.form['id_user']  # enseignant sélectionné dans le select

    db = get_db()
    c = db.cursor()

    # ✅ Colonnes EXACTES de la table groupe
    c.execute(
        "INSERT INTO groupe (nom, id_enseignant) VALUES (?, ?)",
        (nom, id_enseignant)
    )

    # ✅ Récupération automatique de l'id du groupe
    id_groupe = c.lastrowid

    db.commit()
    db.close()

    flash(f"Groupe ajouté avec succès (ID = {id_groupe})")
    return redirect(url_for('admin.gestion_examens'))

@admin_bp.route('/groupe/edit/<int:groupe_id>', methods=['POST'])
@login_required
@admin_required
def edit_groupe(groupe_id):
    db = get_db()
    c = db.cursor()

    # Récupération des champs envoyés par le formulaire inline
    nom = request.form.get("nom")
    id_enseignant = request.form.get("id_enseignant")

    # Validation simple
    if not nom or not id_enseignant:
        flash("Erreur : tous les champs sont requis.", "error")
        return redirect(url_for('admin.gestion_examens'))

    # Mise à jour du groupe dans la base de données
    c.execute("""
        UPDATE groupe
        SET nom = ?, id_enseignant = ?
        WHERE id = ?
    """, (nom, id_enseignant, groupe_id))

    db.commit()
    db.close()

    flash("Groupe modifié avec succès.", "success")
    return redirect(url_for('admin.gestion_examens'))


@admin_bp.route('/groupe/delete/<int:groupe_id>', methods=['POST'])
@login_required
@admin_required
def delete_groupe(groupe_id):
    db = get_db()
    c = db.cursor()

    # Suppression du groupe
    c.execute("DELETE FROM groupe WHERE id = ?", (groupe_id,))
    db.commit()
    db.close()

    flash("Groupe supprimé avec succès.", "success")
    return redirect(url_for('admin.gestion_examens'))


@admin_bp.route('/exam/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    db = get_db()
    c = db.cursor()

    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form.get('description')
        id_matiere = request.form['matiere']
        groupes = request.form.getlist('groupes')   

        id_enseignant = request.form['id_user']

        c.execute("""
            INSERT INTO quiz (
                titre, description, status, id_enseignant, id_matiere
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            titre, description, "brouillon", id_enseignant, id_matiere
        ))

        exam_id = c.lastrowid

        for gid in groupes:
            c.execute("""
                INSERT INTO quiz_groupe (id_quiz, id_groupe)
                VALUES (?, ?)
            """, (exam_id, gid))

        db.commit()
        db.close()

        flash("Quiz créé avec succès")
        return redirect(url_for('admin.gestion_examens'))

    c.execute("SELECT * FROM matiere")
    matieres = [row_to_dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM groupe")
    groupes = [row_to_dict(row) for row in c.fetchall()]

    c.execute("""
        SELECT user.id, user.nom, user.prenom
        FROM user
        JOIN role ON user.id_role = role.id
        WHERE role.user_role = 'enseignant'
    """)
    enseignants = [row_to_dict(row) for row in c.fetchall()]

    db.close()

    return render_template(
        "admin/create_examen.html",
        matieres=matieres,
        groupes=groupes,
        enseignants=enseignants   
    )

@admin_bp.route('/exam/edit/<int:exam_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_exam(exam_id):
    db = get_db()
    c = db.cursor()

    if request.method == 'POST':
        # Récupération sécurisée des champs
        titre = request.form.get('titre')
        description = request.form.get('description', '')
        status = request.form.get('status', 'brouillon')
        id_matiere = request.form.get('matiere')
        id_enseignant = request.form.get('id_user')

        # Vérifications des champs obligatoires
        if not titre or not id_matiere or not id_enseignant:
            flash("Titre, matière et enseignant sont obligatoires")
            return redirect(url_for('admin.edit_exam', exam_id=exam_id))

        # Mise à jour de la base de données
        c.execute("""
            UPDATE quiz
            SET titre=?, description=?, status=?, id_matiere=?, id_enseignant=?
            WHERE id=?
        """, (titre, description, status, id_matiere, id_enseignant, exam_id))

        db.commit()
        db.close()

        flash("Examen modifié avec succès")
        return redirect(url_for('admin.gestion_examens'))

    # =========================
    # PARTIE GET
    # =========================

    # Charger les informations de l'examen
    c.execute("SELECT * FROM quiz WHERE id=?", (exam_id,))
    exam = row_to_dict(c.fetchone())

    # Charger toutes les matières pour le select
    c.execute("SELECT * FROM matiere")
    matieres = [row_to_dict(row) for row in c.fetchall()]

    # Charger tous les enseignants pour le select
    c.execute("""
        SELECT user.id, user.nom, user.prenom
        FROM user
        JOIN role ON user.id_role = role.id
        WHERE role.user_role = 'enseignant'
    """)
    enseignants = [row_to_dict(row) for row in c.fetchall()]

    db.close()

    return render_template(
        "admin/edit_examen.html",
        exam=exam,
        matieres=matieres,
        enseignants=enseignants
    )



@admin_bp.route('/exam/delete/<int:exam_id>', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    db = get_db()
    c = db.cursor()
    c.execute("DELETE FROM quiz WHERE id=?", (exam_id,))
    db.commit()
    db.close()
    flash("Examen supprimé")
    return redirect(url_for('admin.gestion_examens'))



@admin_bp.route('/settings')
@admin_required
def settings():
    """Paramètres généraux du site"""
    return render_template('admin/settings.html')


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
        """Rapports et statistiques globales (dashboard admin)"""
        db = get_db()
        c = db.cursor()

        # --- Statistiques utilisateurs ---
        c.execute("""
            SELECT COUNT(*) as count FROM user
        """)
        total_users = c.fetchone()["count"]
        
        c.execute("""
            SELECT COUNT(*) as count FROM user 
            WHERE date_creation >= datetime('now', '-30 days')
        """)
        active_users = c.fetchone()["count"]
        
        c.execute("""
            SELECT r.user_role, COUNT(*) as count 
            FROM user u
            JOIN role r ON u.id_role = r.id
            GROUP BY r.user_role
        """)
        roles_data = c.fetchall()
        roles_count = {row["user_role"]: row["count"] for row in roles_data}

        # --- Statistiques examens ---
        c.execute("SELECT COUNT(*) as count FROM quiz")
        total_exams = c.fetchone()["count"]
        
        c.execute("SELECT * FROM quiz")
        examens = c.fetchall()
        exams_stats = []
        
        for ex in examens:
            c.execute("SELECT * FROM resultat_quiz WHERE id_quiz = ?", (ex["id"],))
            resultats = c.fetchall()
            nb_etudiants = len(resultats)
            moyenne = round(sum(r["score"] for r in resultats) / nb_etudiants, 2) if nb_etudiants > 0 else 0
            exams_stats.append({
                'id': ex["id"],
                'titre': ex["titre"],
                'nb_etudiants': nb_etudiants,
                'moyenne': moyenne,
                'resultats': resultats
            })

        # --- Examen spécifique à afficher (optionnel) ---
        examen_id = request.args.get('examen_id', type=int)
        examen = None
        resultats_examen = []
        moyenne_examen = 0
        
        if examen_id:
            c.execute("SELECT * FROM quiz WHERE id = ?", (examen_id,))
            examen = row_to_dict(c.fetchone())
            if examen:
                c.execute("SELECT * FROM resultat_quiz WHERE id_quiz = ?", (examen_id,))
                resultats_examen = c.fetchall()
                if resultats_examen:
                    moyenne_examen = round(sum(r["score"] for r in resultats_examen) / len(resultats_examen), 2)

        db.close()

        return render_template(
            'admin/reports.html',
            total_users=total_users,
            active_users=active_users,
            roles_count=roles_count,
            total_exams=total_exams,
            exams_stats=exams_stats,
            examen=examen,
            resultats=resultats_examen,
            moyenne=moyenne_examen
        )
@admin_bp.route('/exam/results')
@login_required
@admin_required
def exam_results():
    """Affiche les résultats de tous les quiz du site"""
    db = get_db()
    c = db.cursor()

    c.execute('''
        SELECT q.*, 
               m.nom AS matiere_nom, 
               u.nom AS enseignant_nom, 
               u.prenom AS enseignant_prenom
        FROM quiz q
        JOIN matiere m ON q.id_matiere = m.id
        JOIN user u ON q.id_enseignant = u.id
        ORDER BY q.id DESC
    ''')
    
    examens_raw = c.fetchall()

    examens = []
    for exam in examens_raw:
        exam_dict = row_to_dict(exam)

        # Récupérer les résultats de l'examen
        c.execute('''
            SELECT r.*, u.nom, u.prenom
            FROM resultat_quiz r
            JOIN user u ON r.id_etudiant = u.id
            WHERE r.id_quiz = ?
            ORDER BY r.score DESC
        ''', (exam_dict['id'],))
        resultats = [row_to_dict(row) for row in c.fetchall()]

        exam_dict['resultats'] = resultats
        exam_dict['matiere'] = {
            'nom': exam_dict.pop('matiere_nom')
        }
        exam_dict['enseignant'] = {
            'nom': exam_dict.pop('enseignant_nom'),
            'prenom': exam_dict.pop('enseignant_prenom')
        }

        examens.append(exam_dict)

    db.close()

    return render_template(
        'admin/exam_results.html',
        examens=examens
    )