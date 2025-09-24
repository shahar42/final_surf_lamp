const express = require('express');
const path = require('path');
const app = express();
const port = process.env.PORT || 3000;

// Serve static files from the current directory
app.use(express.static(__dirname));

// Route for the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    app: 'Marine Biology Trivia',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
});

// API endpoint to get trivia info
app.get('/api/info', (req, res) => {
  res.json({
    name: 'Marine Biology Trivia',
    description: 'Interactive trivia game about ocean life',
    sets: 3,
    questionsPerSet: 6,
    totalQuestions: 18,
    topics: ['Fish & Sea Creatures', 'Coral & Ecosystems', 'Ocean Science']
  });
});

app.listen(port, '0.0.0.0', () => {
  console.log(`🌊 Marine Biology Trivia app listening on port ${port}`);
  console.log(`🐠 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🪸 Ready to test your ocean knowledge!`);
});