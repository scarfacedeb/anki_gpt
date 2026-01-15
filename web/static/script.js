function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const htmlElement = document.documentElement;

    if (savedTheme === 'dark' || (savedTheme !== 'light' && prefersDark)) {
        htmlElement.classList.add('dark-mode');
    }
}

function toggleTheme() {
    const htmlElement = document.documentElement;
    htmlElement.classList.toggle('dark-mode');
    const isDark = htmlElement.classList.contains('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

function toggleDetails(summaryElement) {
    const card = summaryElement.closest('.word-card');
    const details = card.querySelector('.word-details');

    details.classList.toggle('expanded');
}

async function deleteWord(wordId, cardElement) {
    if (!confirm(`Are you sure you want to delete this word?`)) {
        return;
    }

    try {
        const response = await fetch(`/delete/${wordId}?ajax=1`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();

        if (data.success) {
            cardElement.style.opacity = '0';
            cardElement.style.transition = 'opacity 0.3s ease-out';

            setTimeout(() => {
                cardElement.remove();

                const statsElement = document.querySelector('.stats');
                if (statsElement && data.stats) {
                    const totalWords = data.stats.total_words;
                    const synced = data.stats.synced_to_anki;
                    const unsynced = data.stats.unsynced;

                    const showingMatch = statsElement.textContent.match(/\| Showing .+$/);
                    const showingText = showingMatch ? showingMatch[0] : '';

                    statsElement.textContent = `Total words: ${totalWords} | Synced to Anki: ${synced} | Unsynced: ${unsynced}${showingText}`;
                }

                const remainingCards = document.querySelectorAll('.word-card').length;
                if (remainingCards === 0) {
                    location.reload();
                }
            }, 300);
        } else {
            alert('Failed to delete word: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting word:', error);
        alert('Failed to delete word. Please try again.');
    }
}

const pendingAdditions = new Map();

async function quickAddWord() {
    const input = document.getElementById('quickAddInput');
    const dutch = input.value.trim();

    if (!dutch) {
        return;
    }

    if (pendingAdditions.has(dutch)) {
        input.value = '';
        return;
    }

    pendingAdditions.set(dutch, 'pending');
    input.value = '';
    input.focus();
    updateFeedback();

    try {
        const response = await fetch('/quick-add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ dutch })
        });

        const data = await response.json();

        if (data.success) {
            pendingAdditions.set(dutch, 'success');
            updateFeedback();

            await addWordToList(data.word_data);

            setTimeout(() => {
                pendingAdditions.delete(dutch);
                updateFeedback();
            }, 2000);
        } else {
            pendingAdditions.set(dutch, 'error: ' + (data.error || 'Unknown error'));
            updateFeedback();

            setTimeout(() => {
                pendingAdditions.delete(dutch);
                updateFeedback();
            }, 4000);
        }
    } catch (error) {
        console.error('Error adding word:', error);
        pendingAdditions.set(dutch, 'error: Network error');
        updateFeedback();

        setTimeout(() => {
            pendingAdditions.delete(dutch);
            updateFeedback();
        }, 4000);
    }
}

function updateFeedback() {
    const feedback = document.getElementById('quickAddFeedback');

    if (pendingAdditions.size === 0) {
        feedback.style.display = 'none';
        return;
    }

    const items = [];
    for (const [word, status] of pendingAdditions) {
        if (status === 'pending') {
            items.push(`⏳ ${word}`);
        } else if (status === 'success') {
            items.push(`✓ ${word}`);
        } else if (status.startsWith('error:')) {
            items.push(`✗ ${word}: ${status.substring(7)}`);
        }
    }

    feedback.textContent = items.join(' • ');

    const hasError = Array.from(pendingAdditions.values()).some(s => s.startsWith('error:'));
    const hasSuccess = Array.from(pendingAdditions.values()).some(s => s === 'success');
    const hasPending = Array.from(pendingAdditions.values()).some(s => s === 'pending');

    if (hasError) {
        feedback.className = 'quick-add-feedback error';
    } else if (hasPending) {
        feedback.className = 'quick-add-feedback loading';
    } else if (hasSuccess) {
        feedback.className = 'quick-add-feedback success';
    }

    feedback.style.display = 'block';
}

async function addWordToList(wordData) {
    const wordList = document.querySelector('.word-list');
    if (!wordList) return;

    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        if (stats) {
            const statsElement = document.querySelector('.stats');
            if (statsElement) {
                const showingMatch = statsElement.textContent.match(/\| Showing .+$/);
                const showingText = showingMatch ? showingMatch[0] : '';
                statsElement.textContent = `Total words: ${stats.total_words} | Synced to Anki: ${stats.synced_to_anki} | Unsynced: ${stats.unsynced}${showingText}`;
            }
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

let currentRegeneratedData = null;
let currentRegeneratedWordId = null;

async function regenerateWord(wordId, cardElement) {
    const modal = document.getElementById('regenerateModal');
    const loading = document.getElementById('regenerateLoading');
    const comparison = document.getElementById('regenerateComparison');
    const footer = document.getElementById('modalFooter');

    modal.style.display = 'flex';
    loading.style.display = 'block';
    comparison.style.display = 'none';
    footer.style.display = 'none';

    try {
        const response = await fetch(`/regenerate/${wordId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            currentRegeneratedData = data.new;
            currentRegeneratedWordId = wordId;
            displayComparison(data.current, data.new);

            loading.style.display = 'none';
            comparison.style.display = 'grid';
            footer.style.display = 'flex';
        } else {
            alert('Failed to regenerate word: ' + (data.error || 'Unknown error'));
            closeRegenerateModal();
        }
    } catch (error) {
        console.error('Error regenerating word:', error);
        alert('Failed to regenerate word. Please try again.');
        closeRegenerateModal();
    }
}

function displayComparison(current, newData) {
    const currentVersion = document.getElementById('currentVersion');
    const newVersion = document.getElementById('newVersion');

    const fields = [
        { key: 'translation', label: 'Translation' },
        { key: 'pronunciation', label: 'Pronunciation' },
        { key: 'grammar', label: 'Grammar' },
        { key: 'level', label: 'Level' },
        { key: 'definition_nl', label: 'Definition (NL)' },
        { key: 'definition_en', label: 'Definition (EN)' },
        { key: 'collocations', label: 'Collocations', isArray: true },
        { key: 'synonyms', label: 'Synonyms', isArray: true },
        { key: 'related', label: 'Related Words', isArray: true },
        { key: 'examples_nl', label: 'Examples (NL)', isArray: true },
        { key: 'examples_en', label: 'Examples (EN)', isArray: true },
        { key: 'etymology', label: 'Etymology' }
    ];

    currentVersion.innerHTML = fields.map(field => {
        const value = current[field.key];
        const displayValue = field.isArray
            ? (value && value.length > 0 ? value.join(', ') : '<em>None</em>')
            : (value || '<em>None</em>');
        return `
            <div class="comparison-field">
                <div class="comparison-label">${field.label}</div>
                <div class="comparison-value">${displayValue}</div>
            </div>
        `;
    }).join('');

    newVersion.innerHTML = fields.map(field => {
        const value = newData[field.key];
        const displayValue = field.isArray
            ? (value && value.length > 0 ? value.join(', ') : '<em>None</em>')
            : (value || '<em>None</em>');
        return `
            <div class="comparison-field">
                <div class="comparison-label">${field.label}</div>
                <div class="comparison-value">${displayValue}</div>
            </div>
        `;
    }).join('');
}

async function confirmRegeneratedWord() {
    if (!currentRegeneratedData || currentRegeneratedWordId === null) return;

    try {
        const response = await fetch(`/confirm-regenerate/${currentRegeneratedWordId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentRegeneratedData)
        });

        const data = await response.json();

        if (data.success) {
            closeRegenerateModal();
            location.reload();
        } else {
            alert('Failed to save word: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving word:', error);
        alert('Failed to save word. Please try again.');
    }
}

function closeRegenerateModal() {
    const modal = document.getElementById('regenerateModal');
    modal.style.display = 'none';
    currentRegeneratedData = null;
    currentRegeneratedWordId = null;
}

window.onclick = function(event) {
    const modal = document.getElementById('regenerateModal');
    if (event.target === modal) {
        closeRegenerateModal();
    }
    const inlineModal = document.getElementById('inlineRegenerateModal');
    if (event.target === inlineModal) {
        closeInlineRegenerateModal();
    }
}

let regenerationQueue = [];

function updateQueueDisplay() {
    const queueBox = document.getElementById('regenerationQueue');
    const queueList = document.getElementById('regenerationQueueList');
    const queueCount = document.getElementById('queueCount');
    const approveAllBtn = document.getElementById('approveAllBtn');

    if (regenerationQueue.length === 0) {
        queueBox.style.display = 'none';
        return;
    }

    queueBox.style.display = 'block';
    queueCount.textContent = regenerationQueue.length;

    queueList.innerHTML = regenerationQueue.map((item, index) => `
        <div class="queue-item" onclick="showQueuedItem(${index})">
            <span class="queue-word">${item.data.current.dutch}</span>
            <button class="queue-remove" onclick="event.stopPropagation(); removeFromQueue(${index})" title="Remove">
                <i data-lucide="x" style="width: 14px; height: 14px;"></i>
            </button>
        </div>
    `).join('');

    lucide.createIcons();
}

function removeFromQueue(index) {
    regenerationQueue.splice(index, 1);
    updateQueueDisplay();
}

function showQueuedItem(index) {
    const item = regenerationQueue[index];
    if (!item) return;

    currentQueueIndex = index;

    displayInlineComparison(item.data.current, item.data.new);

    const modal = document.getElementById('inlineRegenerateModal');
    modal.style.display = 'flex';
}

let currentQueueIndex = null;

async function regenerateWordInline(wordId, buttonElement) {
    buttonElement.classList.add('loading');
    buttonElement.disabled = true;

    try {
        const response = await fetch(`/regenerate/${wordId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            regenerationQueue.push({
                data: data,
                id: wordId,
                dutch: data.current.dutch
            });

            updateQueueDisplay();

            buttonElement.classList.remove('loading');
            buttonElement.disabled = false;
        } else {
            alert('Failed to regenerate word: ' + (data.error || 'Unknown error'));
            buttonElement.classList.remove('loading');
            buttonElement.disabled = false;
        }
    } catch (error) {
        console.error('Error regenerating word:', error);
        alert('Failed to regenerate word. Please try again.');
        buttonElement.classList.remove('loading');
        buttonElement.disabled = false;
    }
}

function displayInlineComparison(current, newData) {
    const currentVersion = document.getElementById('inlineCurrentVersion');
    const newVersion = document.getElementById('inlineNewVersion');

    const fields = [
        { key: 'translation', label: 'Translation' },
        { key: 'pronunciation', label: 'Pronunciation' },
        { key: 'grammar', label: 'Grammar' },
        { key: 'level', label: 'Level' },
        { key: 'definition_nl', label: 'Definition (NL)' },
        { key: 'definition_en', label: 'Definition (EN)' },
        { key: 'collocations', label: 'Collocations', isArray: true },
        { key: 'synonyms', label: 'Synonyms', isArray: true },
        { key: 'related', label: 'Related Words', isArray: true },
        { key: 'examples_nl', label: 'Examples (NL)', isArray: true },
        { key: 'examples_en', label: 'Examples (EN)', isArray: true },
        { key: 'etymology', label: 'Etymology' }
    ];

    currentVersion.innerHTML = fields.map(field => {
        const value = current[field.key];
        const displayValue = field.isArray
            ? (value && value.length > 0 ? value.join(', ') : '<em>None</em>')
            : (value || '<em>None</em>');
        return `
            <div class="comparison-field">
                <div class="comparison-label">${field.label}</div>
                <div class="comparison-value">${displayValue}</div>
            </div>
        `;
    }).join('');

    newVersion.innerHTML = fields.map(field => {
        const value = newData[field.key];
        const displayValue = field.isArray
            ? (value && value.length > 0 ? value.join(', ') : '<em>None</em>')
            : (value || '<em>None</em>');
        return `
            <div class="comparison-field">
                <div class="comparison-label">${field.label}</div>
                <div class="comparison-value">${displayValue}</div>
            </div>
        `;
    }).join('');
}

async function confirmInlineRegeneratedWord() {
    if (currentQueueIndex === null || !regenerationQueue[currentQueueIndex]) return;

    const item = regenerationQueue[currentQueueIndex];

    try {
        const response = await fetch(`/confirm-regenerate/${item.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(item.data.new)
        });

        const data = await response.json();

        if (data.success) {
            regenerationQueue.splice(currentQueueIndex, 1);
            updateQueueDisplay();

            closeInlineRegenerateModal();

            if (regenerationQueue.length === 0) {
                location.reload();
            }
        } else {
            alert('Failed to save word: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error saving word:', error);
        alert('Failed to save word. Please try again.');
    }
}

async function approveAll() {
    if (regenerationQueue.length === 0) return;

    const approveAllBtn = document.getElementById('approveAllBtn');
    approveAllBtn.disabled = true;
    approveAllBtn.textContent = 'Approving...';

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < regenerationQueue.length; i++) {
        const item = regenerationQueue[i];
        try {
            const response = await fetch(`/confirm-regenerate/${item.id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(item.data.new)
            });

            const data = await response.json();

            if (data.success) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            console.error('Error saving word:', error);
            failCount++;
        }
    }

    regenerationQueue = [];
    updateQueueDisplay();

    alert(`Approved ${successCount} words. ${failCount > 0 ? `Failed: ${failCount}` : ''}`);
    location.reload();
}

function closeInlineRegenerateModal() {
    const modal = document.getElementById('inlineRegenerateModal');
    modal.style.display = 'none';
    currentQueueIndex = null;
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
});
