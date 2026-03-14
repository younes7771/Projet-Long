from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.database import get_db
from utils.decorators import login_required, etudiant_required
from datetime import datetime
import sqlite3
import random


etudiant_bp = Blueprint('etudiant', __name__)

def row_to_dict(row):
    """Convertit un objet Row en dictionnaire"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

@etudiant_bp.route('/dashboard')
@login_required
@etudiant_required
def dashboard():
    db = get_db()
    c = db.cursor()
    
    # Récupérer les quiz disponibles pour le groupe de l'étudiant et la somme des durée de chaque questions pour afficher la durée du quiz
    c.execute('''
        SELECT DISTINCT q.*, m.nom as matiere_nom, 
        ROUND(COALESCE(SUM(qu.duree), 0) / 60.0, 2) as duree_totale_minutes
        FROM quiz q 
        JOIN matiere m ON q.id_matiere = m.id 
        LEFT JOIN quiz_groupe qg ON q.id = qg.id_quiz 
        LEFT JOIN question qu ON q.id = qu.id_quiz
        WHERE q.status = "publié" 
        AND (qg.id_groupe = ? OR qg.id_groupe IS NULL)
        GROUP BY q.id
    ''', (session['id_groupe'],))

    
    quiz_disponibles = [row_to_dict(row) for row in c.fetchall()]
    


        # MODIFICATION: Récupérer les IDs des quiz déjà passés par l'étudiant
    c.execute('''
        SELECT DISTINCT id_quiz FROM resultat_quiz WHERE id_etudiant = ?
    ''', (session['user_id'],))
    quiz_passes = {row['id_quiz'] for row in c.fetchall()}
    
    # MODIFICATION: Ajouter le flag 'already_taken' à chaque quiz
    for quiz in quiz_disponibles:
        quiz['already_taken'] = quiz['id'] in quiz_passes
    


    # Récupérer les résultats existants
    c.execute('''
        SELECT r.*, q.titre 
        FROM resultat_quiz r 
        JOIN quiz q ON r.id_quiz = q.id 
        WHERE r.id_etudiant = ? 
        ORDER BY r.date_soumission DESC
    ''', (session['user_id'],))
    
    resultats = [row_to_dict(row) for row in c.fetchall()]
    
    db.close()
    return render_template('etudiant/dashboard.html', quiz=quiz_disponibles, resultats=resultats)

@etudiant_bp.route('/quiz/<int:quiz_id>/take')
@login_required
@etudiant_required
def take_quiz(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Vérifier si l'étudiant a déjà passé ce quiz
    c.execute('SELECT * FROM resultat_quiz WHERE id_quiz = ? AND id_etudiant = ?', (quiz_id, session['user_id']))
    resultat_existant = c.fetchone()
    
    if resultat_existant:
        flash('Vous avez déjà passé ce quiz!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Récupérer les informations du quiz
    c.execute('SELECT q.* FROM quiz q WHERE q.id = ?', (quiz_id,))
    quiz = row_to_dict(c.fetchone())
    
    if not quiz:
        flash('Quiz non trouvé!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Récupérer les questions
    c.execute("SELECT * FROM question WHERE id_quiz = ?", (quiz_id,))
    questions = [row_to_dict(row) for row in c.fetchall()]

    # Randomiser l'ordre des questions
    random.shuffle(questions)
    
    questions_with_choix = []
    for q in questions:
        c.execute("SELECT * FROM choix_reponse WHERE id_question = ?", (q['id'],))
        choix = [row_to_dict(row) for row in c.fetchall()]
        questions_with_choix.append({
            'question': q, 
            'choix': choix,
            'duree_restante': q.get('duree', 60)
        })
    
    db.close()
    return render_template('etudiant/take_quiz.html', quiz=quiz, questions=questions_with_choix, quiz_id=quiz_id)

@etudiant_bp.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
@etudiant_required
def submit_quiz(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Vérifier si l'étudiant a déjà passé ce quiz
    c.execute('SELECT * FROM resultat_quiz WHERE id_quiz = ? AND id_etudiant = ?', (quiz_id, session['user_id']))
    if c.fetchone():
        flash('Vous avez déjà passé ce quiz!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Calculer le score
    c.execute("SELECT * FROM question WHERE id_quiz = ?", (quiz_id,))
    questions = [row_to_dict(row) for row in c.fetchall()]
    
    score_total = 0
    reponses_correctes = 0
    total_questions = len(questions)
    
    # Sauvegarder le résultat d'abord
    c.execute('INSERT INTO resultat_quiz (id_quiz, id_etudiant, score) VALUES (?, ?, ?)', 
             (quiz_id, session['user_id'], 0))  # Score temporaire
    resultat_id = c.lastrowid
    
    # Traiter chaque question et sauvegarder les réponses
    for question in questions:
        qid = question['id']
        est_correct = False
        points = 0
        
        if question['type'] == 'numerique':
            reponse_text = request.form.get(f'question_{qid}', '')
            if reponse_text:
                points = question['bareme']
                est_correct = True
                score_total += points
                reponses_correctes += 1
                
                # Sauvegarder la réponse
                c.execute('''
                    INSERT INTO reponse_etudiant 
                    (id_resultat, id_question, texte_reponse, est_correct, points_obtenus) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (resultat_id, qid, reponse_text, est_correct, points))
                
        else:
            choix_selectionnes = request.form.getlist(f'question_{qid}')
            if choix_selectionnes:
                c.execute('SELECT id FROM choix_reponse WHERE id_question = ? AND est_correct = 1', (qid,))
                corrects = [str(r['id']) for r in c.fetchall()]
                
                # Vérifier si la réponse est correcte
                est_correct = set(choix_selectionnes) == set(corrects)
                
                if est_correct:
                    points = question['bareme']
                    score_total += points
                    reponses_correctes += 1
                
                # Sauvegarder chaque choix sélectionné
                for choix_id in choix_selectionnes:
                    c.execute('''
                        INSERT INTO reponse_etudiant 
                        (id_resultat, id_question, id_choix, est_correct, points_obtenus) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', (resultat_id, qid, choix_id, est_correct, points if est_correct else 0))
    
    # Mettre à jour le score final
    c.execute('UPDATE resultat_quiz SET score = ? WHERE id = ?', (score_total, resultat_id))
    
    db.commit()
    db.close()
    
    flash(f'Quiz soumis avec succès! Score: {score_total}/{sum(q["bareme"] for q in questions)}')
    return redirect(url_for('etudiant.view_results', quiz_id=quiz_id))

@etudiant_bp.route('/quiz/<int:quiz_id>/feedback', methods=['POST'])
@login_required
@etudiant_required
def submit_feedback(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Vérifier que l'étudiant a bien passé ce quiz
    c.execute('SELECT * FROM resultat_quiz WHERE id_quiz = ? AND id_etudiant = ?', 
              (quiz_id, session['user_id']))
    if not c.fetchone():
        flash('Vous devez avoir passé le quiz pour donner un feedback')
        return redirect(url_for('etudiant.dashboard'))
    
    # Vérifier si un feedback existe déjà
    c.execute('SELECT * FROM feedback WHERE id_quiz = ? AND id_etudiant = ?', 
              (quiz_id, session['user_id']))
    if c.fetchone():
        flash('Vous avez déjà donné un feedback pour ce quiz')
        return redirect(url_for('etudiant.view_results', quiz_id=quiz_id))
    
    # Récupérer les données du formulaire
    texte = request.form.get('texte', '').strip()
    note = request.form.get('note')
    
    if not texte:
        flash('Le commentaire est obligatoire')
        return redirect(url_for('etudiant.view_results', quiz_id=quiz_id))
    
    # Insérer le feedback
    if note:
        c.execute('INSERT INTO feedback (id_quiz, id_etudiant, texte, note) VALUES (?, ?, ?, ?)',
                 (quiz_id, session['user_id'], texte, int(note)))
    else:
        c.execute('INSERT INTO feedback (id_quiz, id_etudiant, texte) VALUES (?, ?, ?)',
                 (quiz_id, session['user_id'], texte))
    
    db.commit()
    db.close()
    
    flash('Merci pour votre feedback!')
    return redirect(url_for('etudiant.view_results', quiz_id=quiz_id))



@etudiant_bp.route('/results/<int:quiz_id>')
@login_required
@etudiant_required
def view_results(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Récupérer le résultat
    c.execute('''
        SELECT r.*, q.titre, u.nom, u.prenom 
        FROM resultat_quiz r 
        JOIN quiz q ON r.id_quiz = q.id 
        JOIN user u ON r.id_etudiant = u.id 
        WHERE r.id_quiz = ? AND r.id_etudiant = ?
    ''', (quiz_id, session['user_id']))
    
    resultat = row_to_dict(c.fetchone())
    
    if not resultat:
        flash('Résultat non trouvé!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Récupérer les informations du quiz
    c.execute('SELECT * FROM question WHERE id_quiz = ?', (quiz_id,))
    questions = [row_to_dict(row) for row in c.fetchall()]
    
    total_questions = len(questions)
    points_max = sum(q['bareme'] for q in questions)
    
    # Récupérer le feedback existant
    c.execute('SELECT * FROM feedback WHERE id_quiz = ? AND id_etudiant = ?', 
              (quiz_id, session['user_id']))
    feedback_existant = row_to_dict(c.fetchone())
    
    db.close()
    
    return render_template('etudiant/results.html', 
                         resultat=resultat, 
                         total_questions=total_questions,
                         points_max=points_max,
                     

    feedback_existant=feedback_existant)









@etudiant_bp.route('/correction/<int:quiz_id>')
@login_required
@etudiant_required
def view_correction(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Récupérer le résultat
    c.execute('''
        SELECT r.*, q.titre, u.nom, u.prenom 
        FROM resultat_quiz r 
        JOIN quiz q ON r.id_quiz = q.id 
        JOIN user u ON r.id_etudiant = u.id 
        WHERE r.id_quiz = ? AND r.id_etudiant = ?
    ''', (quiz_id, session['user_id']))
    
    resultat = row_to_dict(c.fetchone())
    
    if not resultat:
        flash('Résultat non trouvé!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Récupérer toutes les questions avec leurs détails
    c.execute('''
        SELECT q.*, 
               (SELECT COUNT(*) FROM reponse_etudiant re 
                WHERE re.id_question = q.id AND re.id_resultat = ?) as a_repondu
        FROM question q 
        WHERE q.id_quiz = ?
        ORDER BY q.id
    ''', (resultat['id'], quiz_id))
    
    questions = [row_to_dict(row) for row in c.fetchall()]
    
    questions_with_details = []
    for question in questions:
        # Récupérer les choix possibles
        c.execute('SELECT * FROM choix_reponse WHERE id_question = ?', (question['id'],))
        choix = [row_to_dict(row) for row in c.fetchall()]
        
        # Récupérer les réponses de l'étudiant
        c.execute('''
            SELECT re.*, cr.texte as choix_texte, cr.est_correct as choix_est_correct
            FROM reponse_etudiant re
            LEFT JOIN choix_reponse cr ON re.id_choix = cr.id
            WHERE re.id_resultat = ? AND re.id_question = ?
        ''', (resultat['id'], question['id']))
        
        reponses = [row_to_dict(row) for row in c.fetchall()]
        
        questions_with_details.append({
            'question': question,
            'choix': choix,
            'reponses': reponses,
            'bareme': question['bareme']
        })
    
    db.close()
    
    return render_template('etudiant/correction.html', 
                         resultat=resultat, 
                         questions=questions_with_details)








@etudiant_bp.route('/correction/<int:quiz_id>/export')
@login_required
@etudiant_required
def export_correction(quiz_id):
    db = get_db()
    c = db.cursor()
    
    # Récupérer le résultat
    c.execute('''
        SELECT r.*, q.titre, u.nom, u.prenom 
        FROM resultat_quiz r 
        JOIN quiz q ON r.id_quiz = q.id 
        JOIN user u ON r.id_etudiant = u.id 
        WHERE r.id_quiz = ? AND r.id_etudiant = ?
    ''', (quiz_id, session['user_id']))
    
    resultat = row_to_dict(c.fetchone())
    
    if not resultat:
        flash('Résultat non trouvé!')
        return redirect(url_for('etudiant.dashboard'))
    
    # Récupérer les questions et réponses
    c.execute('''
        SELECT q.*, 
               GROUP_CONCAT(cr.texte, '|') as choix_textes,
               GROUP_CONCAT(cr.est_correct, '|') as choix_corrects
        FROM question q
        LEFT JOIN choix_reponse cr ON q.id = cr.id_question
        WHERE q.id_quiz = ?
        GROUP BY q.id
    ''', (quiz_id,))
    
    questions = [row_to_dict(row) for row in c.fetchall()]
    
    # Préparer le contenu HTML pour l'export
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Correction - {resultat['titre']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #2c3e50; }}
            .header {{ margin-bottom: 30px; }}
            .student-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
            .question {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
            .correct {{ color: green; font-weight: bold; }}
            .incorrect {{ color: red; }}
            .reponse {{ margin: 10px 0; padding: 10px; background: #f8f9fa; }}
        </style>
    </head>
    <body>
        <h1>Correction détaillée - {resultat['titre']}</h1>
        <div class="header">
            <p><strong>Étudiant:</strong> {resultat['prenom']} {resultat['nom']}</p>
            <p><strong>Date:</strong> {resultat['date_soumission']}</p>
            <p><strong>Score final:</strong> {resultat['score']} points</p>
        </div>
    """
    
    for i, q in enumerate(questions, 1):
        # Récupérer les réponses de l'étudiant pour cette question
        c.execute('''
            SELECT re.*, cr.texte as choix_texte
            FROM reponse_etudiant re
            LEFT JOIN choix_reponse cr ON re.id_choix = cr.id
            WHERE re.id_resultat = ? AND re.id_question = ?
        ''', (resultat['id'], q['id']))
        
        reponses = c.fetchall()
        
        html_content += f"""
        <div class="question">
            <h3>Question {i}</h3>
            <p><strong>Énoncé:</strong> {q['enonce']}</p>
            <p><strong>Type:</strong> {q['type']}</p>
            <p><strong>Barème:</strong> {q['bareme']} points</p>
            <div class="reponse">
                <strong>Votre réponse:</strong><br>
        """
        
        if q['type'] == 'numerique':
            reponse_text = reponses[0]['texte_reponse'] if reponses else "Non répondue"
            html_content += f"<p>{reponse_text}</p>"
        else:
            if reponses:
                for r in reponses:
                    status = "correct" if r['est_correct'] else "incorrect"
                    html_content += f"<p class='{status}'>- {r['choix_texte']}</p>"
            else:
                html_content += "<p>Aucune réponse</p>"
        
        # Indiquer si la réponse est correcte
        points = reponses[0]['points_obtenus'] if reponses else 0
        html_content += f"<p><strong>Points obtenus:</strong> {points}/{q['bareme']}</p>"
        html_content += "</div></div>"
    
    html_content += """
    </body>
    </html>
    """
    
    db.close()
    
    # Créer un fichier HTML à télécharger
    from flask import send_file
    import io
    
    # Pour PDF, nous pouvons utiliser weasyprint ou pdfkit
    # Version simple : export HTML
    return send_file(
        io.BytesIO(html_content.encode('utf-8')),
        mimetype='text/html',
        as_attachment=True,
        download_name=f'correction_{resultat["titre"]}_{session["nom"]}.html'
    )