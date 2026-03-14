class QuestionTimer {
    constructor(questionId, duration, onTimeout) {
        this.questionId = questionId;
        this.duration = duration;
        this.remainingTime = duration;
        this.onTimeout = onTimeout;
        this.timerInterval = null;
    }

    start() {
        this.updateDisplay();
        this.timerInterval = setInterval(() => {
            this.remainingTime--;
            this.updateDisplay();

            if (this.remainingTime <= 0) {
                this.stop();
                if (this.onTimeout) {
                    this.onTimeout(this.questionId);
                }
            }
        }, 1000);
    }

    stop() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateDisplay() {
        const minutes = Math.floor(this.remainingTime / 60);
        const seconds = this.remainingTime % 60;
        const display = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

        const timerElement = document.getElementById(`timer-${this.questionId}`);
        if (timerElement) {
            timerElement.textContent = display;
            timerElement.style.color = this.remainingTime < 30 ? '#e74c3c' : '';
            timerElement.style.fontWeight = this.remainingTime < 30 ? 'bold' : '';
        }
    }
}

class QuizManager {
    constructor() {
        this.currentTimer = null;
        this.currentQuestionIndex = 0;
        this.questions = [];
    }

    initialize(questions) {
        this.questions = questions;
        this.showQuestion(0);
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.getElementById('next-btn').addEventListener('click', () => this.nextQuestion());
    }

    showQuestion(index) {
        if (this.currentTimer) {
            this.currentTimer.stop();
        }

        document.querySelectorAll('.question-container').forEach(container => {
            container.style.display = 'none';
        });

        const currentQuestion = this.questions[index];
        const questionElement = document.getElementById(`question-${currentQuestion.question.id}`);
        if (questionElement) {
            questionElement.style.display = 'block';
        }

        this.currentTimer = new QuestionTimer(
            currentQuestion.question.id,
            currentQuestion.question.duree,
            () => this.onQuestionTimeout()
        );
        this.currentTimer.start();

        this.currentQuestionIndex = index;
        this.updateNavigation();
    }

    onQuestionTimeout() {
        this.nextQuestion();
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.showQuestion(this.currentQuestionIndex + 1);
        }
    }

    updateNavigation() {
        const nextBtn = document.getElementById('next-btn');
        const submitBtn = document.getElementById('submit-btn');

        if (nextBtn) nextBtn.style.display = this.currentQuestionIndex < this.questions.length - 1 ? 'inline-block' : 'none';
        if (submitBtn) submitBtn.style.display = this.currentQuestionIndex === this.questions.length - 1 ? 'inline-block' : 'none';
    }
}

let quizManager;

document.addEventListener('DOMContentLoaded', function () {
    if (window.questionsData && window.questionsData.length > 0) {
        quizManager = new QuizManager();
        quizManager.initialize(window.questionsData);
    }
});