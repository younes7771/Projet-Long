import sqlite3
from werkzeug.security import generate_password_hash

def create_admin_user():
    """Crée un utilisateur admin pour les tests"""
    db = sqlite3.connect('quiz.db')
    c = db.cursor()
    
    # Vérifier si l'admin existe déjà
    c.execute("SELECT id FROM user WHERE email = 'admin@quiz.com'")
    if c.fetchone():
        print("L'utilisateur admin existe déjà!")
        db.close()
        return
    
    # Récupérer l'ID du rôle admin
    c.execute("SELECT id FROM role WHERE user_role = 'admin'")
    role_id = c.fetchone()
    
    if not role_id:
        # Créer le rôle admin s'il n'existe pas
        c.execute("INSERT INTO role (user_role) VALUES ('admin')")
        c.execute("SELECT id FROM role WHERE user_role = 'admin'")
        role_id = c.fetchone()
    
    # Créer l'utilisateur admin
    password_hash = generate_password_hash('admin123')
    c.execute('''
        INSERT INTO user (nom, prenom, email, password_hash, id_role) 
        VALUES (?, ?, ?, ?, ?)
    ''', ('Admin', 'System', 'admin@quiz.com', password_hash, role_id[0]))
    
    db.commit()
    db.close()
    print("Utilisateur admin créé avec succès!")
    print("Email: admin@quiz.com")
    print("Mot de passe: admin123")

if __name__ == '__main__':
    create_admin_user()