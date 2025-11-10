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

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', initTheme);
