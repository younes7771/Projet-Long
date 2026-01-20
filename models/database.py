import sqlite3
from flask import g
import os

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('quiz.db')
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect('quiz.db')
    c = db.cursor()
    
    # Vérifier si les tables existent déjà
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='role'")
    tables_exist = c.fetchone()
    
    if not tables_exist:
        # Créer les tables seulement si elles n'existent pas
        c.executescript('''
            CREATE TABLE IF NOT EXISTS role (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_role VARCHAR(255) CHECK (user_role IN ('admin', 'enseignant', 'etudiant')) NOT NULL UNIQUE
            );
            
            CREATE TABLE IF NOT EXISTS groupe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom VARCHAR(100) NOT NULL,
                id_enseignant INTEGER NOT NULL,
                FOREIGN KEY (id_enseignant) REFERENCES user (id),
                UNIQUE(nom,id_enseignant)
            );
            
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom VARCHAR(100) NOT NULL,
                prenom VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                id_role INTEGER NOT NULL,
                id_groupe INTEGER,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_hash TEXT NOT NULL,
                FOREIGN KEY (id_role) REFERENCES role (id),
                FOREIGN KEY (id_groupe) REFERENCES groupe (id)
            );
            
            CREATE TABLE IF NOT EXISTS matiere (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_enseignant INTEGER NOT NULL,
                nom VARCHAR(100) NOT NULL,
                FOREIGN KEY (id_enseignant) REFERENCES user (id),
                UNIQUE(nom,id_enseignant)
            );
            
            CREATE TABLE IF NOT EXISTS quiz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titre VARCHAR(200) NOT NULL,
                description TEXT,
                status TEXT CHECK (status IN ('brouillon', 'publié', 'terminé')) DEFAULT 'brouillon',
                id_enseignant INTEGER NOT NULL,
                id_matiere INTEGER NOT NULL,
                FOREIGN KEY (id_enseignant) REFERENCES user (id),
                FOREIGN KEY (id_matiere) REFERENCES matiere (id)
            );
            
            CREATE TABLE IF NOT EXISTS question (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enonce TEXT NOT NULL,
                type TEXT CHECK (type IN ('QCM_simple', 'QCM_multiple', 'Vrai_Faux', 'numerique')) NOT NULL,
                bareme FLOAT DEFAULT 1.0,
                duree INTEGER DEFAULT 60,
                id_quiz INTEGER,
                banque_question INTEGER DEFAULT 0,
                id_enseignant INTEGER NOT NULL,
                FOREIGN KEY (id_quiz) REFERENCES quiz (id) ON DELETE CASCADE,
                FOREIGN KEY (id_enseignant) REFERENCES user (id)
            );
            
            CREATE TABLE IF NOT EXISTS choix_reponse (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_question INTEGER NOT NULL,
                texte TEXT NOT NULL,
                est_correct BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (id_question) REFERENCES question (id) ON DELETE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS quiz_groupe (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_quiz INTEGER NOT NULL,
                id_groupe INTEGER NOT NULL,
                FOREIGN KEY (id_quiz) REFERENCES quiz (id),
                FOREIGN KEY (id_groupe) REFERENCES groupe (id)
            );
            
            CREATE TABLE IF NOT EXISTS resultat_quiz (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_quiz INTEGER NOT NULL,
                id_etudiant INTEGER NOT NULL,
                score FLOAT NOT NULL,
                date_soumission TIMESTAMP DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (id_quiz) REFERENCES quiz (id),
                FOREIGN KEY (id_etudiant) REFERENCES user (id),
                UNIQUE(id_quiz, id_etudiant)
            );
            
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_quiz INTEGER NOT NULL,
                id_etudiant INTEGER NOT NULL,
                texte TEXT NOT NULL,
                note INTEGER CHECK (note >= 1 AND note <= 5),
                date_creation TIMESTAMP DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (id_quiz) REFERENCES quiz (id),
                FOREIGN KEY (id_etudiant) REFERENCES user (id),
                UNIQUE(id_quiz, id_etudiant)
            );
        ''')
        
        # Insérer les rôles de base
        c.execute("INSERT OR IGNORE INTO role (user_role) VALUES ('admin'), ('enseignant'), ('etudiant')")
        print("Base de données initialisée avec succès!")
    else:
        print("Base de données existe déjà, conservation des données...")
    
    db.commit()
    db.close()