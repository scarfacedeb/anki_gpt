// Dark mode toggle with system preference detection
function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const htmlElement = document.documentElement;

    // Apply dark mode if: explicitly saved as dark, OR no saved preference and system prefers dark
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

// Word details expand/collapse
function toggleDetails(summaryElement) {
    const card = summaryElement.closest('.word-card');
    const details = card.querySelector('.word-details');

    details.classList.toggle('expanded');
}

// Delete word without page reload
async function deleteWord(dutch, cardElement) {
    if (!confirm(`Are you sure you want to delete ${dutch}?`)) {
        return;
    }

    try {
        const response = await fetch(`/delete/${encodeURIComponent(dutch)}?ajax=1`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();

        if (data.success) {
            // Remove the card from DOM with fade out animation
            cardElement.style.opacity = '0';
            cardElement.style.transition = 'opacity 0.3s ease-out';

            setTimeout(() => {
                cardElement.remove();

                // Update stats in header
                const statsElement = document.querySelector('.stats');
                if (statsElement && data.stats) {
                    const totalWords = data.stats.total_words;
                    const synced = data.stats.synced_to_anki;
                    const unsynced = data.stats.unsynced;

                    // Find the part before "Showing" to preserve pagination info
                    const showingMatch = statsElement.textContent.match(/\| Showing .+$/);
                    const showingText = showingMatch ? showingMatch[0] : '';

                    statsElement.textContent = `Total words: ${totalWords} | Synced to Anki: ${synced} | Unsynced: ${unsynced}${showingText}`;
                }

                // If no more cards on page, reload to show next page or empty state
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

// Regenerate word
let currentRegeneratedData = null;

async function regenerateWord(dutch, cardElement) {
    const modal = document.getElementById('regenerateModal');
    const loading = document.getElementById('regenerateLoading');
    const comparison = document.getElementById('regenerateComparison');
    const footer = document.getElementById('modalFooter');

    // Show modal with loading state
    modal.style.display = 'flex';
    loading.style.display = 'block';
    comparison.style.display = 'none';
    footer.style.display = 'none';

    try {
        const response = await fetch(`/regenerate/${encodeURIComponent(dutch)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            currentRegeneratedData = data.new;
            displayComparison(data.current, data.new);

            // Show comparison and footer
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
    if (!currentRegeneratedData) return;

    try {
        const response = await fetch(`/confirm-regenerate/${encodeURIComponent(currentRegeneratedData.dutch)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(currentRegeneratedData)
        });

        const data = await response.json();

        if (data.success) {
            closeRegenerateModal();
            // Reload the page to show updated word
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
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('regenerateModal');
    if (event.target === modal) {
        closeRegenerateModal();
    }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', initTheme);
