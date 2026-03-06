import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'votre_cle_secrete_ici_changez_la'
    DATABASE = 'quiz.db'
    DEBUG = True


        # Configuration email
    MAIL_SERVER = 'smtp.gmail.com'  # Pour Gmail
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or 'evalyquiz@gmail.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or 'jzyshhzniumrmxmu'
    MAIL_DEFAULT_SENDER = 'noreply@evalyquiz.com'