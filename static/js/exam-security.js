class ExamSecurity {
    constructor() {
        this.isFullScreen = false;
        this.exitAttempts = 0;
        this.warningShown = false;
    }

    init() {
        this.requestFullScreen();
        this.blockNavigation();
        this.blockShortcuts();
        this.blockContextMenu();
        this.blockSelection();
        this.monitorFocus();
    }

    requestFullScreen() {
        const element = document.documentElement;
        
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.webkitRequestFullscreen) {
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) {
            element.msRequestFullscreen();
        }

        // Détecter la sortie du plein écran
        document.addEventListener('fullscreenchange', () => this.onFullScreenChange());
        document.addEventListener('webkitfullscreenchange', () => this.onFullScreenChange());
        document.addEventListener('mozfullscreenchange', () => this.onFullScreenChange());
        document.addEventListener('MSFullscreenChange', () => this.onFullScreenChange());
    }

    onFullScreenChange() {
        if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
            this.exitAttempts++;
            
            if (this.exitAttempts >= 3) {
                alert('Tentative de sortie du mode examen détectée ! Le quiz va être soumis automatiquement.');
                document.getElementById('quiz-form').submit();
            } else {
                alert(`⚠️ Vous devez rester en mode plein écran pour l'examen. Tentative ${this.exitAttempts}/3`);
                this.requestFullScreen();
            }
        }
    }

    blockNavigation() {
        // Bloquer le bouton retour du navigateur
        window.addEventListener('popstate', (event) => {
            history.pushState(null, null, location.href);
            alert('Navigation interdite pendant l\'examen');
        });

        // Empêcher la fermeture de l'onglet
        window.addEventListener('beforeunload', (e) => {
            e.preventDefault();
            e.returnValue = 'Voulez-vous vraiment quitter l\'examen ?';
            return e.returnValue;
        });

        // Bloquer le rafraîchissement
        window.addEventListener('keydown', (e) => {
            if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                alert('Rafraîchissement interdit pendant l\'examen');
            }
        });
    }

    blockShortcuts() {
        window.addEventListener('keydown', (e) => {
            // Bloquer Alt+Tab, Alt+F4, Ctrl+W, etc.
            if (e.altKey || (e.ctrlKey && (e.key === 'w' || e.key === 't' || e.key === 'n'))) {
                e.preventDefault();
                if (!this.warningShown) {
                    alert('Raccourcis clavier désactivés pendant l\'examen');
                    this.warningShown = true;
                    setTimeout(() => this.warningShown = false, 5000);
                }
            }

            // Bloquer la touche Windows
            if (e.key === 'Meta' || e.key === 'OS') {
                e.preventDefault();
            }
        });
    }

    blockContextMenu() {
        // Bloquer le clic droit
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            alert('Clic droit désactivé pendant l\'examen');
        });
    }

    blockSelection() {
        // Empêcher la sélection de texte
        document.addEventListener('selectstart', (e) => e.preventDefault());
        
        // CSS pour bloquer la sélection
        const style = document.createElement('style');
        style.textContent = `
            * {
                user-select: none !important;
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
            }
        `;
        document.head.appendChild(style);
    }

    monitorFocus() {
        // Détecter quand la fenêtre perd le focus
        window.addEventListener('blur', () => {
            if (!this.warningShown) {
                alert('⚠️ Vous avez quitté la fenêtre du quiz. Restez concentré !');
                this.warningShown = true;
                setTimeout(() => this.warningShown = false, 5000);
            }
        });
    }
}

// Initialisation automatique quand la page charge
document.addEventListener('DOMContentLoaded', () => {
    // Ne pas initialiser si ce n'est pas une page d'examen
    if (document.getElementById('quiz-form')) {
        const security = new ExamSecurity();
        security.init();
    }
});