document.getElementById('decide-btn').addEventListener('click', () => {
    const siblingsInput = document.getElementById('siblings').value;
    const choreInput = document.getElementById('chore').value;
    const resultDiv = document.getElementById('result');

    if (!siblingsInput || !choreInput) {
        resultDiv.textContent = 'Please enter sibling names and a chore.';
        return;
    }

    const siblings = siblingsInput.split(',').map(s => s.trim());
    const randomSibling = siblings[Math.floor(Math.random() * siblings.length)];

    resultDiv.textContent = `${randomSibling} has to ${choreInput}!`;
});