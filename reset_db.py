import os
import sqlite3

def reset_database():
    """Réinitialise complètement la base de données"""
    if os.path.exists('quiz.db'):
        confirm = input("Êtes-vous sûr de vouloir supprimer toutes les données? (oui/non): ")
        if confirm.lower() == 'oui':
            os.remove('quiz.db')
            print("Base de données supprimée.")
        else:
            print("Annulé.")
            return
    
    # Recréer une base propre
    import models.database
    models.database.init_db()
    print("Base de données réinitialisée avec succès!")

if __name__ == '__main__':
    reset_database()