const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

// Game variables
let ballX = canvas.width / 2;
let ballY = canvas.height / 2;
let ballSpeedX = 10;
let ballSpeedY = 4;

let player1Y = 250;
let player2Y = 250;
const paddleHeight = 100;
const paddleWidth = 10;

let player1Score = 0;
let player2Score = 0;
const winningScore = 5;

let showingWinScreen = false;

function handleMouseClick(evt) {
    if (showingWinScreen) {
        player1Score = 0;
        player2Score = 0;
        showingWinScreen = false;
    }
}

window.onload = function() {
    canvas.addEventListener('mousedown', handleMouseClick);

    canvas.addEventListener('mousemove',
        function(evt) {
            const rect = canvas.getBoundingClientRect();
            const root = document.documentElement;
            const mouseY = evt.clientY - rect.top - root.scrollTop;
            player1Y = mouseY - paddleHeight / 2;
        });

    const framesPerSecond = 30;
    setInterval(function() {
        moveEverything();
        drawEverything();
    }, 1000 / framesPerSecond);
};

function ballReset() {
    if (player1Score >= winningScore || player2Score >= winningScore) {
        showingWinScreen = true;
    }

    ballSpeedX = -ballSpeedX;
    ballX = canvas.width / 2;
    ballY = canvas.height / 2;
}

function computerMovement() {
    const player2YCenter = player2Y + (paddleHeight / 2);
    if (player2YCenter < ballY - 35) {
        player2Y += 6;
    } else if (player2YCenter > ballY + 35) {
        player2Y -= 6;
    }
}

function moveEverything() {
    if (showingWinScreen) {
        return;
    }

    computerMovement();

    ballX += ballSpeedX;
    ballY += ballSpeedY;

    if (ballX < 0) {
        if (ballY > player1Y && ballY < player1Y + paddleHeight) {
            ballSpeedX = -ballSpeedX;

            const deltaY = ballY - (player1Y + paddleHeight / 2);
            ballSpeedY = deltaY * 0.35;
        } else {
            player2Score++;
            ballReset();
        }
    }
    if (ballX > canvas.width) {
        if (ballY > player2Y && ballY < player2Y + paddleHeight) {
            ballSpeedX = -ballSpeedX;

            const deltaY = ballY - (player2Y + paddleHeight / 2);
            ballSpeedY = deltaY * 0.35;
        } else {
            player1Score++;
            ballReset();
        }
    }

    if (ballY < 0) {
        ballSpeedY = -ballSpeedY;
    }
    if (ballY > canvas.height) {
        ballSpeedY = -ballSpeedY;
    }
}

function drawNet() {
    for (let i = 0; i < canvas.height; i += 40) {
        colorRect(canvas.width / 2 - 1, i, 2, 20, 'white');
    }
}

function drawEverything() {
    // black background
    colorRect(0, 0, canvas.width, canvas.height, 'black');

    if (showingWinScreen) {
        ctx.fillStyle = 'white';

        if (player1Score >= winningScore) {
            ctx.fillText("Left Player Won!", 350, 200);
        } else if (player2Score >= winningScore) {
            ctx.fillText("Right Player Won!", 350, 200);
        }

        ctx.fillText("click to continue", 350, 500);
        return;
    }

    drawNet();

    // left player paddle
    colorRect(0, player1Y, paddleWidth, paddleHeight, 'white');

    // right computer paddle
    colorRect(canvas.width - paddleWidth, player2Y, paddleWidth, paddleHeight, 'white');

    // ball
    colorCircle(ballX, ballY, 10, 'white');

    ctx.fillText(player1Score, 100, 100);
    ctx.fillText(player2Score, canvas.width - 100, 100);
}

function colorCircle(centerX, centerY, radius, drawColor) {
    ctx.fillStyle = drawColor;
    ctx.beginPath();
    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2, true);
    ctx.fill();
}

function colorRect(leftX, topY, width, height, drawColor) {
    ctx.fillStyle = drawColor;
    ctx.fillRect(leftX, topY, width, height);
}
