from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3

def row_to_dict(row):
    """Convertit un objet Row sqlite3 en dictionnaire"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

def format_duration(seconds):
    """Formate une durée en secondes vers MM:SS"""
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def calculate_score(quiz_id, reponses):
    """Calcule le score d'un quiz"""
    db = sqlite3.connect('quiz.db')
    db.row_factory = sqlite3.Row
    c = db.cursor()
    
    c.execute("SELECT * FROM question WHERE id_quiz = ?", (quiz_id,))
    questions = c.fetchall()
    
    score_total = 0
    for question in questions:
        qid = question['id']
        if question['type'] == 'numerique':
            if reponses.get(f'question_{qid}'):
                score_total += question['bareme']
        else:
            choix_selectionnes = reponses.getlist(f'question_{qid}')
            if choix_selectionnes:
                c.execute('SELECT id FROM choix_reponse WHERE id_question = ? AND est_correct = 1', (qid,))
                corrects = [str(r['id']) for r in c.fetchall()]
                if set(choix_selectionnes) == set(corrects):
                    score_total += question['bareme']
    
    db.close()
    return score_total