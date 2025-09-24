document.addEventListener('DOMContentLoaded', () => {
    const siblingNameInput = document.getElementById('sibling-name');
    const addSiblingButton = document.getElementById('add-sibling');
    const siblingList = document.getElementById('sibling-list');
    const decideChoreButton = document.getElementById('decide-chore');
    const winnerDisplay = document.getElementById('winner');

    let siblings = [];

    addSiblingButton.addEventListener('click', addSibling);
    siblingNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            addSibling();
        }
    });

    decideChoreButton.addEventListener('click', () => {
        if (siblings.length > 0) {
            const randomIndex = Math.floor(Math.random() * siblings.length);
            const winner = siblings[randomIndex];
            winnerDisplay.textContent = `🎉 ${winner} gets to do the chore! 🎉`;
        } else {
            winnerDisplay.textContent = 'Please add some siblings first!';
        }
    });

    function addSibling() {
        const name = siblingNameInput.value.trim();
        if (name) {
            siblings.push(name);
            renderSiblings();
            siblingNameInput.value = '';
            siblingNameInput.focus();
        }
    }

    function renderSiblings() {
        siblingList.innerHTML = '';
        siblings.forEach((sibling, index) => {
            const li = document.createElement('li');
            li.textContent = sibling;
            
            const removeButton = document.createElement('button');
            removeButton.textContent = 'X';
            removeButton.classList.add('remove-sibling');
            removeButton.addEventListener('click', () => {
                siblings.splice(index, 1);
                renderSiblings();
            });

            li.appendChild(removeButton);
            siblingList.appendChild(li);
        });
    }
});
