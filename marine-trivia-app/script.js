// Marine Biology Trivia Questions
const triviaData = {
    1: {
        name: "🐟 Fish & Sea Creatures",
        questions: [
            {
                question: "What is the largest fish in the ocean?",
                answers: ["Great White Shark", "Whale Shark", "Blue Whale", "Manta Ray"],
                correct: 1
            },
            {
                question: "How many hearts does an octopus have?",
                answers: ["1", "2", "3", "4"],
                correct: 2
            },
            {
                question: "What do sea turtles use to navigate long distances?",
                answers: ["Stars", "Ocean currents", "Earth's magnetic field", "Sound waves"],
                correct: 2
            },
            {
                question: "Which sea creature can change its color to match its surroundings?",
                answers: ["Seahorse", "Jellyfish", "Cuttlefish", "Sea urchin"],
                correct: 2
            },
            {
                question: "What is the fastest fish in the ocean?",
                answers: ["Sailfish", "Marlin", "Tuna", "Barracuda"],
                correct: 0
            },
            {
                question: "How do dolphins primarily communicate?",
                answers: ["Body language", "Echolocation clicks", "Color changes", "Electrical signals"],
                correct: 1
            }
        ]
    },
    2: {
        name: "🪸 Coral & Ecosystems",
        questions: [
            {
                question: "What provides energy to coral reefs through photosynthesis?",
                answers: ["Algae", "Plankton", "Fish waste", "Ocean currents"],
                correct: 0
            },
            {
                question: "Which zone of the ocean receives no sunlight?",
                answers: ["Twilight zone", "Midnight zone", "Abyssal zone", "Hadal zone"],
                correct: 2
            },
            {
                question: "What causes coral bleaching?",
                answers: ["Cold water", "Too much food", "Warm water stress", "Strong currents"],
                correct: 2
            },
            {
                question: "Which ecosystem is often called the 'nursery of the sea'?",
                answers: ["Coral reefs", "Kelp forests", "Mangroves", "Seagrass beds"],
                correct: 2
            },
            {
                question: "What percentage of marine life depends on coral reefs?",
                answers: ["10%", "25%", "40%", "60%"],
                correct: 1
            },
            {
                question: "Which ocean zone contains the most biodiversity?",
                answers: ["Surface waters", "Deep sea", "Coral reefs", "Open ocean"],
                correct: 2
            }
        ]
    },
    3: {
        name: "🌊 Ocean Science",
        questions: [
            {
                question: "What percentage of Earth's surface is covered by oceans?",
                answers: ["65%", "71%", "78%", "82%"],
                correct: 1
            },
            {
                question: "Which ocean is the deepest?",
                answers: ["Atlantic", "Pacific", "Indian", "Arctic"],
                correct: 1
            },
            {
                question: "What causes ocean tides?",
                answers: ["Wind", "Earth's rotation", "Moon's gravity", "Ocean currents"],
                correct: 2
            },
            {
                question: "How much of the ocean has been explored?",
                answers: ["Less than 5%", "About 20%", "Around 50%", "More than 75%"],
                correct: 0
            },
            {
                question: "What is the average depth of the ocean?",
                answers: ["2 miles", "2.3 miles", "3.1 miles", "4.2 miles"],
                correct: 1
            },
            {
                question: "Which process removes salt from seawater?",
                answers: ["Filtration", "Boiling", "Desalination", "Crystallization"],
                correct: 2
            }
        ]
    }
};

// Game State
let currentSet = 1;
let currentQuestion = 0;
let score = 0;
let selectedAnswer = null;
let setScores = {1: 0, 2: 0, 3: 0};
let completedSets = new Set();

// DOM Elements
const screens = {
    menu: document.getElementById('main-menu'),
    quiz: document.getElementById('quiz-screen'),
    results: document.getElementById('results-screen'),
    final: document.getElementById('final-results')
};

const elements = {
    questionText: document.getElementById('question-text'),
    answers: document.getElementById('answers'),
    questionCounter: document.getElementById('question-counter'),
    setName: document.getElementById('set-name'),
    progress: document.getElementById('progress'),
    nextBtn: document.getElementById('next-btn'),
    scoreText: document.getElementById('score-text'),
    scoreMessage: document.getElementById('score-message'),
    nextSetBtn: document.getElementById('next-set-btn')
};

// Screen Management
function showScreen(screenName) {
    Object.values(screens).forEach(screen => screen.classList.remove('active'));
    screens[screenName].classList.add('active');
}

// Start a trivia set
function startSet(setNumber) {
    currentSet = setNumber;
    currentQuestion = 0;
    score = 0;
    selectedAnswer = null;

    showScreen('quiz');
    loadQuestion();
    updateUI();
}

// Load current question
function loadQuestion() {
    const questionData = triviaData[currentSet].questions[currentQuestion];

    elements.questionText.textContent = questionData.question;
    elements.answers.innerHTML = '';

    questionData.answers.forEach((answer, index) => {
        const button = document.createElement('button');
        button.className = 'answer-btn';
        button.textContent = answer;
        button.onclick = () => selectAnswer(index);
        elements.answers.appendChild(button);
    });

    selectedAnswer = null;
    elements.nextBtn.disabled = true;
    elements.nextBtn.textContent = currentQuestion === 5 ? 'Finish Set' : 'Next Question';
}

// Select an answer
function selectAnswer(index) {
    if (selectedAnswer !== null) return; // Prevent multiple selections

    selectedAnswer = index;
    const questionData = triviaData[currentSet].questions[currentQuestion];
    const answerButtons = document.querySelectorAll('.answer-btn');

    answerButtons.forEach((btn, i) => {
        btn.classList.remove('selected');
        if (i === questionData.correct) {
            btn.classList.add('correct');
        } else if (i === index && i !== questionData.correct) {
            btn.classList.add('incorrect');
        }
    });

    if (index === questionData.correct) {
        score++;
    }

    elements.nextBtn.disabled = false;

    // Auto-advance after 1.5 seconds
    setTimeout(() => {
        if (selectedAnswer !== null) {
            nextQuestion();
        }
    }, 1500);
}

// Move to next question
function nextQuestion() {
    if (currentQuestion < 5) {
        currentQuestion++;
        loadQuestion();
        updateUI();
    } else {
        finishSet();
    }
}

// Update UI elements
function updateUI() {
    elements.questionCounter.textContent = `Question ${currentQuestion + 1} of 6`;
    elements.setName.textContent = triviaData[currentSet].name;
    elements.progress.style.width = `${((currentQuestion + 1) / 6) * 100}%`;
}

// Finish current set
function finishSet() {
    setScores[currentSet] = score;
    completedSets.add(currentSet);

    elements.scoreText.textContent = `${score}/6`;

    let message = '';
    if (score === 6) message = '🌟 Perfect! You\'re a marine biology expert!';
    else if (score >= 4) message = '🐠 Great job! You know your ocean facts!';
    else if (score >= 2) message = '🌊 Not bad! Keep learning about the sea!';
    else message = '🐙 Keep exploring! The ocean has many secrets!';

    elements.scoreMessage.textContent = message;

    // Show/hide next set button
    if (completedSets.size === 3) {
        elements.nextSetBtn.style.display = 'none';
    } else {
        elements.nextSetBtn.style.display = 'inline-block';
        const nextSetNumber = getNextSet();
        if (nextSetNumber) {
            elements.nextSetBtn.textContent = `Next: ${triviaData[nextSetNumber].name}`;
        }
    }

    showScreen('results');

    // Check if all sets completed
    if (completedSets.size === 3) {
        setTimeout(() => showFinalResults(), 3000);
    }
}

// Get next available set
function getNextSet() {
    for (let i = 1; i <= 3; i++) {
        if (!completedSets.has(i)) {
            return i;
        }
    }
    return null;
}

// Start next set
function nextSet() {
    const nextSetNumber = getNextSet();
    if (nextSetNumber) {
        startSet(nextSetNumber);
    }
}

// Show final results
function showFinalResults() {
    const totalScore = setScores[1] + setScores[2] + setScores[3];
    document.getElementById('total-score').textContent = `${totalScore}/18`;
    document.getElementById('set1-score').textContent = `${setScores[1]}/6`;
    document.getElementById('set2-score').textContent = `${setScores[2]}/6`;
    document.getElementById('set3-score').textContent = `${setScores[3]}/6`;

    let finalMessage = '';
    if (totalScore >= 16) finalMessage = '🏆 Outstanding! You\'re a true marine biologist!';
    else if (totalScore >= 12) finalMessage = '🐋 Excellent! You have great ocean knowledge!';
    else if (totalScore >= 8) finalMessage = '🐠 Good work! You\'re learning about marine life!';
    else finalMessage = '🌊 Keep exploring! The ocean world awaits you!';

    document.getElementById('final-message').textContent = finalMessage;

    showScreen('final');
}

// Navigation functions
function goHome() {
    showScreen('menu');
}

function resetQuiz() {
    completedSets.clear();
    setScores = {1: 0, 2: 0, 3: 0};
    showScreen('menu');
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    showScreen('menu');
});