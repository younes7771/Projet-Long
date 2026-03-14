from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models.database import get_db
from utils.decorators import login_required, enseignant_required
from datetime import datetime
from xhtml2pdf import pisa
import csv
import io
import sqlite3

enseignant_bp = Blueprint('enseignant', __name__)

def row_to_dict(row):
    """Convertit un objet Row en dictionnaire"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

@enseignant_bp.route('/question/<int:question_id>/edit', methods=['GET', 'POST'])
@login_required
@enseignant_required
def edit_question(question_id):
    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM question WHERE id = ?", (question_id,))
    question = row_to_dict(c.fetchone())

    if not question:
        flash("Question introuvable")
        return redirect(url_for('enseignant.dashboard'))

    c.execute("SELECT * FROM choix_reponse WHERE id_question = ?", (question_id,))
    choix = [row_to_dict(row) for row in c.fetchall()]

    if request.method == 'POST':
        enonce = request.form['enonce']
        bareme = request.form['bareme']
        duree = request.form['duree']

        if question['type'] == 'numerique':
            reponse_correcte = request.form['reponse_correcte']
            c.execute("""
                UPDATE question
                SET enonce = ?, bareme = ?, duree = ?, reponse_correcte = ?
                WHERE id = ?
            """, (enonce, bareme, duree, reponse_correcte, question_id))

        else:
            c.execute("""
                UPDATE question
                SET enonce = ?, bareme = ?, duree = ?
                WHERE id = ?
            """, (enonce, bareme, duree, question_id))

            c.execute("DELETE FROM choix_reponse WHERE id_question = ?", (question_id,))
            choix_list = request.form.getlist("choix[]")
            corrects = request.form.getlist("correct[]")

            for i, ch in enumerate(choix_list):
                if ch.strip():
                    est_correct = str(i) in corrects
                    c.execute("""
                        INSERT INTO choix_reponse (id_question, texte, est_correct)
                        VALUES (?, ?, ?)
                    """, (question_id, ch, est_correct))

        db.commit()
        flash("Question modifiée avec succès")
        return redirect(url_for('enseignant.edit_quiz', quiz_id=question['id_quiz']))

    db.close()
    return render_template("enseignant/edit_question.html", question=question, choix=choix)

@enseignant_bp.route('/question/<int:question_id>/delete')
@login_required
@enseignant_required
def delete_question(question_id):
    db = get_db()
    c = db.cursor()

    c.execute("SELECT id_quiz FROM question WHERE id = ?", (question_id,))
    row = c.fetchone()

    if not row:
        flash("Question introuvable")
        return redirect(url_for('enseignant.dashboard'))

    quiz_id = row['id_quiz']

    c.execute("DELETE FROM choix_reponse WHERE id_question = ?", (question_id,))

    c.execute("DELETE FROM question WHERE id = ?", (question_id,))

    db.commit()
    db.close()

    flash("Question supprimée avec succès")
    return redirect(url_for('enseignant.edit_quiz', quiz_id=quiz_id))

@enseignant_bp.route('/dashboard')
@login_required
@enseignant_required
def dashboard():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM matiere WHERE id_enseignant = ?", (session['user_id'],))
    matieres = [row_to_dict(row) for row in c.fetchall()]
    c.execute("SELECT * FROM quiz WHERE id_enseignant = ?", (session['user_id'],))
    quiz = [row_to_dict(row) for row in c.fetchall()]
    c.execute("SELECT * FROM groupe WHERE id_enseignant = ?", (session['user_id'],))
    groupes = [row_to_dict(row) for row in c.fetchall()]
    db.close()
    return render_template('enseignant/dashboard.html', matieres=matieres, quiz=quiz, groupes=groupes)

@enseignant_bp.route('/matiere/add', methods=['POST'])
@login_required
@enseignant_required
def add_matiere():
    nom = request.form['nom'].strip().capitalize()
    db = get_db()
    c = db.cursor()
    try:
        c.execute("INSERT INTO matiere (nom, id_enseignant) VALUES (?, ?)", (nom, session['user_id']))
        db.commit()
        flash('Matière ajoutée')
    except sqlite3.IntegrityError:
            flash(f'La matière "{nom}" existe deja dans votre liste')
    finally:
        db.close()
    
    return redirect(url_for('enseignant.dashboard'))

@enseignant_bp.route('/groupe/add', methods=['POST'])
@login_required
@enseignant_required
def add_groupe():
    nom = request.form['nom'].strip().capitalize()
    db = get_db()
    c = db.cursor()
    try:
        c.execute("INSERT INTO groupe (nom, id_enseignant) VALUES (?, ?)", (nom, session['user_id']))
        db.commit()
        flash('Groupe ajouté')
    except sqlite3.IntegrityError:
            flash(f'Le groupe "{nom}" existe deja dans votre liste')
    finally:
        db.close()
    
    return redirect(url_for('enseignant.dashboard'))

@enseignant_bp.route('/quiz/create', methods=['GET', 'POST'])
@login_required
@enseignant_required
def create_quiz():
    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form['description']
        # duree = request.form['duree']
        id_matiere = request.form['matiere']
        groupes = request.form.getlist('groupes')
        
        db = get_db()
        c = db.cursor()
        c.execute('INSERT INTO quiz (titre, description, id_enseignant, id_matiere) VALUES (?, ?, ?, ?)', 
                 (titre, description, session['user_id'], id_matiere))
        quiz_id = c.lastrowid
        
        for groupe_id in groupes:
            c.execute('INSERT INTO quiz_groupe (id_quiz, id_groupe) VALUES (?, ?)', (quiz_id, groupe_id))
        
        db.commit()
        db.close()
        flash('Quiz créé')
        return redirect(url_for('enseignant.edit_quiz', quiz_id=quiz_id))
    
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM matiere WHERE id_enseignant = ?", (session['user_id'],))
    matieres = [row_to_dict(row) for row in c.fetchall()]
    c.execute("SELECT * FROM groupe WHERE id_enseignant = ?", (session['user_id'],))
    groupes = [row_to_dict(row) for row in c.fetchall()]
    db.close()
    return render_template('enseignant/create_quiz.html', matieres=matieres, groupes=groupes)


@enseignant_bp.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
@enseignant_required
def edit_quiz(quiz_id):
    db = get_db()
    c = db.cursor()
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_question':
            enonce = request.form['enonce']
            type_q = request.form['type']
            bareme = request.form['bareme']
            duree = request.form.get('duree_question', 60)

            ajouter_banque_question = 1 if request.form.get('ajouter_banque_question') else 0

            if type_q=='Vrai_Faux':
                bonne_reponse_vf=request.form.get('correct_vf')
                if not bonne_reponse_vf:
                    flash("Erreur:Vous devez indiquer si la reponse est vrai ou Faux.","error")
                    return redirect(url_for('enseignant.edit_quiz',quiz_id=quiz_id))
                c.execute('INSERT INTO question (enonce, type, bareme, duree, id_quiz, id_enseignant,banque_question) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                    (enonce, type_q, bareme, duree, quiz_id, session['user_id'], ajouter_banque_question))
                question_id = c.lastrowid
                c.execute('INSERT INTO choix_reponse(id_question,texte,est_correct) VALUES (?,?,?)',
                          (question_id,"Vrai",(bonne_reponse_vf=='vrai')))
                c.execute('INSERT INTO choix_reponse(id_question,texte,est_correct) VALUES (?,?,?)',
                          (question_id,"Faux",(bonne_reponse_vf=='faux')))
            
            elif type_q in ['QCM_simple', 'QCM_multiple']:
                choix = request.form.getlist('choix[]')
                corrects = request.form.getlist('correct[]')

                if not corrects:
                    flash("Erreur:Vous devez au moins selectionner au moins une bonne reponse.","error")
                    return redirect(url_for('enseignant.edit_quiz',quiz_id=quiz_id))
                if type_q == 'QCM_simple'and len(corrects)>1:
                    flash("Erreur:Un QCM simple ne peut avoir qu'une seule bonne reponse.","error")
                    return redirect(url_for('enseignant.edit_quiz',quiz_id=quiz_id))
                choix_valides=[c for c in choix if c.strip()]
                if len(choix_valides)<2:
                    flash("Erreur:Un QCM doit avoir au moins 2 choix de réponses possibles.","error")
                    return redirect(url_for('enseignant.edit_quiz',quiz_id=quiz_id))
                c.execute('INSERT INTO question(enonce,type,bareme,duree,id_quiz,id_enseignant,banque_question) VALUES(?,?,?,?,?,?,?)',
                          (enonce,type_q,bareme,duree,quiz_id,session['user_id'],ajouter_banque_question))
                question_id=c.lastrowid
                for i, choix_texte in enumerate(choix):
                    if choix_texte.strip():
                        est_correct = str(i) in corrects
                        c.execute('INSERT INTO choix_reponse (id_question, texte, est_correct) VALUES (?, ?, ?)', 
                                 (question_id, choix_texte, est_correct))
            elif type_q=='numerique':
                bonne_reponse_num=request.form.get('bonne_reponse_num')
                if not bonne_reponse_num:
                    flash("Erreur:Vous devez saisir une reponse numerique","error")
                    return redirect(url_for('enseignant.edit_quiz',quiz_id=quiz_id))
                c.execute('''INSERT INTO question(enonce,type,bareme,duree,id_quiz,id_enseignant) VALUES(?,?,?,?,?,?)''',(enonce,type_q,bareme,duree,quiz_id,session['user_id']))
                question_id=c.lastrowid
                c.execute('''INSERT INTO choix_reponse(id_question,texte,est_correct) VALUES(?,?,?)''',(question_id,bonne_reponse_num,1))

            else:
                pass
            db.commit()
            flash('Question ajoutée')
        elif action== 'import_from_bank':
            question_id_source=request.form.get('question_id_banque')
            c.execute("SELECT * FROM question WHERE id = ? ",(question_id_source,))
            question_data=c.fetchone()
            if question_data:
                c.execute('''INSERT INTO question (enonce,type,bareme,duree,id_quiz,id_enseignant,banque_question) VALUES (?,?,?,?,?,?,?)''',(question_data['enonce'],question_data['type'],question_data['bareme'],question_data['duree'],quiz_id,session['user_id'],1))
                new_question_id=c.lastrowid
                c.execute("SELECT * FROM choix_reponse WHERE id_question = ?",(question_id_source,))
                choix_sources = c.fetchall()
                for choix_source in choix_sources:
                    c.execute("INSERT INTO choix_reponse(id_question,texte,est_correct) VALUES (?,?,?)",(new_question_id,choix_source['texte'],choix_source['est_correct']))
                db.commit()
                flash('Question importee avec succes')
        elif action == 'publish':
            c.execute("SELECT COUNT(*) as count FROM question WHERE id_quiz=?",(quiz_id,))
            nb_questions=c.fetchone()['count']
            if nb_questions==0:
                flash("Impossible de publier un quiz valide.")
            else:
                c.execute("UPDATE quiz SET status = 'publié' WHERE id = ?", (quiz_id,))
                db.commit()
                return redirect(url_for('enseignant.dashboard'))  
    c.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,))
    quiz = row_to_dict(c.fetchone())
    c.execute(
            '''SELECT question.* FROM question 
                JOIN quiz ON question.id_quiz=quiz.id 
                WHERE quiz.id_matiere = ? 
                AND question.id_enseignant = ? 
                AND question.banque_question = 1 
                AND question.id_quiz != ?''',
                (quiz['id_matiere'],session['user_id'],quiz_id))
    banque_questions=[row_to_dict(row) for  row in c.fetchall()]
    c.execute("SELECT * FROM question WHERE id_quiz = ?", (quiz_id,))
    questions = [row_to_dict(row) for row in c.fetchall()]
    
    questions_avec_choix = []
    for q in questions:
        c.execute("SELECT * FROM choix_reponse WHERE id_question = ?", (q['id'],))
        choix = [row_to_dict(row) for row in c.fetchall()]
        questions_avec_choix.append({'question': q, 'choix': choix})
    
    db.close()
    return render_template('enseignant/edit_quiz.html', quiz=quiz, questions=questions_avec_choix,banque=banque_questions)

@enseignant_bp.route('/statistiques/<int:quiz_id>')
@login_required
@enseignant_required
def statistiques(quiz_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,))
    quiz = row_to_dict(c.fetchone())
    
    c.execute('''
        SELECT r.*, u.nom, u.prenom 
        FROM resultat_quiz r 
        JOIN user u ON r.id_etudiant = u.id 
        WHERE r.id_quiz = ? 
        ORDER BY r.score DESC
    ''', (quiz_id,))
    
    resultats = [row_to_dict(row) for row in c.fetchall()]
    scores = [r['score'] for r in resultats if r['score'] is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    db.close()
    return render_template('enseignant/statistiques.html', quiz=quiz, resultats=resultats, avg_score=avg_score)

@enseignant_bp.route('/export/<int:quiz_id>')
@login_required
@enseignant_required
def export_quiz(quiz_id):
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM quiz WHERE id = ?", (quiz_id,))
    quiz = row_to_dict(c.fetchone())
    
    c.execute('''
        SELECT r.*, u.nom, u.prenom 
        FROM resultat_quiz r 
        JOIN user u ON r.id_etudiant = u.id 
        WHERE r.id_quiz = ? 
        ORDER BY r.score DESC
    ''', (quiz_id,))
    
    resultats = [row_to_dict(row) for row in c.fetchall()]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Étudiant', 'Date', 'Score'])
    for r in resultats:
        writer.writerow([f"{r['prenom']} {r['nom']}", r['date_soumission'], r['score']])
    output.seek(0)
    db.close()
    
    return send_file(io.BytesIO(output.getvalue().encode()), 
                    mimetype='text/csv', 
                    as_attachment=True, 
                    download_name=f'quiz_{quiz_id}_results.csv')


@enseignant_bp.route('/export_pdf/<int:quiz_id>')
@login_required
@enseignant_required
def export_quiz_pdf(quiz_id):
    db=get_db()
    c=db.cursor()
    c.execute("SELECT * FROM quiz WHERE id=?",(quiz_id,))
    quiz=row_to_dict(c.fetchone())

    c.execute('''
        SELECT r.*,u.nom,u.prenom
        FROM resultat_quiz r
        JOIN user u ON r.id_etudiant=u.id
        WHERE r.id_quiz= ?
        ORDER BY r.score DESC
    ''',(quiz_id,))
    resultats=[row_to_dict(row) for row in c.fetchall()]
    db.close()

    scores = [r['score'] for r in resultats if r['score'] is not None]
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_score = round(avg_score, 2)

    html_content=render_template('enseignant/pdf_template.html',quiz=quiz,resultats=resultats,avg_score=avg_score)

    pdf_output=io.BytesIO()

    pisa_status=pisa.CreatePDF(
        src=html_content,
        dest=pdf_output
    )
    if pisa_status.err:
        return"Une erreur est survenue lors de la creation du PDF",500
    pdf_output.seek(0)

    return send_file(
        pdf_output,
        mimetype='appliction/pdf',
        as_attachment=True,
        download_name=f'Resultats_{quiz["titre"]}.pdf'
    )

@enseignant_bp.route('/export_quiz_content_pdf/<int:quiz_id>')
@login_required
@enseignant_required
def export_quiz_content_pdf(quiz_id):
    db=get_db()
    c=db.cursor()

    c.execute("SELECT * FROM quiz WHERE id = ?",(quiz_id,))
    quiz=row_to_dict(c.fetchone())

    if not quiz:
        flash('Quiz introuvable')
        return redirect(url_for('enseignant.dashboard'))
    
    c.execute("SELECT * FROM question WHERE id_quiz=?",(quiz_id,))
    questions=[row_to_dict(row) for row in c.fetchall()]

    total_duree_secondes=sum(q['duree'] for q in questions if q['duree'])
    total_duree_minutes=int(total_duree_secondes/60)
    quiz['duree']=total_duree_minutes

    questions_avec_choix=[]
    for q in questions:
        c.execute("SELECT * FROM choix_reponse WHERE id_question=?",(q['id'],))
        choix=[row_to_dict(row) for row in c.fetchall()]
        questions_avec_choix.append({'question':q,'choix':choix})

    db.close()

    html_content=render_template(
        'enseignant/quiz_print_template.html',
        quiz=quiz,
        questions=questions_avec_choix
    )
    pdf_output=io.BytesIO()
    pisa_status=pisa.CreatePDF(
        src=html_content,
        dest=pdf_output
    )
    if pisa_status.err:
        return"Une erreur est survenue lors de la creation du PDF",500
    pdf_output.seek(0)

    return send_file(
        pdf_output,
        mimetype='application.pdf',
        as_attachment=True,
        download_name=f'Sujet_{quiz["titre"]}.pdf'
    )
@enseignant_bp.route('/quiz/<int:quiz_id>/feedback')
@login_required
@enseignant_required
def etudiant_feedback(quiz_id):
    db= get_db()
    c=db.cursor()
    c.execute("SELECT titre FROM quiz WHERE id = ? AND id_enseignant = ?",(quiz_id,session['user_id']))
    quiz=c.fetchone()
    if not quiz:
        flash("Quiz introuvable")
        return redirect(url_for('enseignant.dashboard'))
    c.execute('''SELECT texte, IFNULL(note, 0) as note,date_creation FROM feedback WHERE feedback.id_quiz = ? ORDER BY date_creation DESC''',(quiz_id,))
    feedback=[row_to_dict(row) for row in c.fetchall()]
    db.close()
    return render_template('enseignant/feedback.html',quiz=quiz,feedback=feedback)