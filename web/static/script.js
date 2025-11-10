function toggleDetails(summaryElement) {
    const card = summaryElement.closest('.word-card');
    const details = card.querySelector('.word-details');
    const expandBtn = card.querySelector('.expand-btn');

    details.classList.toggle('expanded');
    expandBtn.classList.toggle('expanded');
}
