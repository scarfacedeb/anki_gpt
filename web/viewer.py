"""
Simple HTML viewer for browsing the local word database.
"""
import sys
from pathlib import Path

# Add parent directory to path to import from main package
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from urllib.parse import urlencode
from db import WordDatabase
from word import Word

# Load environment variables
load_dotenv()

app = Flask(__name__)
db = WordDatabase()

def build_pagination_url(page, query, sort_by, order):
    """Build URL query string for pagination."""
    params = {'page': page, 'sort': sort_by, 'order': order}
    if query:
        params['q'] = query
    return urlencode(params)

# Make the function available in templates
app.jinja_env.globals.update(get_pagination_url=build_pagination_url)

def get_words_with_timestamps(query=None):
    """Get words with their updated_at timestamps."""
    import sqlite3
    from pathlib import Path

    db_path = Path("words.db")
    words_data = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if query:
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT *, updated_at FROM words
                WHERE dutch LIKE ? OR translation LIKE ?
                   OR definition_nl LIKE ? OR definition_en LIKE ?
                ORDER BY created_at DESC
            """, (search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute("SELECT *, updated_at FROM words ORDER BY created_at DESC")

        rows = cursor.fetchall()
        for row in rows:
            word = db._dict_to_word(dict(row))
            updated_at = row['updated_at']
            words_data.append((word, updated_at))

    return words_data

@app.route('/')
def index():
    """Main page showing all words or search results with pagination."""
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'dutch')  # Default sort by dutch word
    order = request.args.get('order', 'asc')  # Default ascending
    page = int(request.args.get('page', 1))  # Current page
    per_page = 100  # Words per page

    all_words = get_words_with_timestamps(query if query else None)

    # Sort words
    reverse = (order == 'desc')
    if sort_by == 'dutch':
        all_words.sort(key=lambda w: w[0].dutch.lower(), reverse=reverse)
    elif sort_by == 'translation':
        all_words.sort(key=lambda w: w[0].translation.lower(), reverse=reverse)
    elif sort_by == 'grammar':
        all_words.sort(key=lambda w: w[0].grammar.lower(), reverse=reverse)

    # Pagination
    total_words = len(all_words)
    total_pages = (total_words + per_page - 1) // per_page  # Ceiling division
    page = min(page, max(1, total_pages))  # Ensure page is within valid range

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    words_data = all_words[start_idx:end_idx]

    # Calculate page range to show (e.g., 1 2 3 ... last)
    page_range = []
    if total_pages <= 7:
        # Show all pages if 7 or fewer
        page_range = list(range(1, total_pages + 1))
    else:
        # Show first 3, current page area, and last page
        if page <= 3:
            page_range = list(range(1, 5)) + ['...', total_pages]
        elif page >= total_pages - 2:
            page_range = [1, '...'] + list(range(total_pages - 3, total_pages + 1))
        else:
            page_range = [1, '...', page - 1, page, page + 1, '...', total_pages]

    stats = db.get_stats()

    return render_template(
        'index.html',
        words_data=words_data,
        stats=stats,
        query=query,
        sort_by=sort_by,
        order=order,
        page=page,
        total_pages=total_pages,
        page_range=page_range,
        total_words=total_words,
        showing_count=len(words_data),
        showing_start=start_idx + 1 if words_data else 0,
        showing_end=start_idx + len(words_data),
        zip=zip
    )

@app.route('/delete/<path:dutch>', methods=['POST'])
def delete_word(dutch):
    """Delete a word from the database."""
    success = db.delete_word(dutch)
    if success:
        print(f"Deleted word: {dutch}")
    else:
        print(f"Failed to delete word: {dutch}")

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax'):
        if success:
            stats = db.get_stats()
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete word'}), 400

    # Regular form submission - redirect
    return redirect(url_for('index'))

@app.route('/edit/<path:dutch>', methods=['GET'])
def edit_word(dutch):
    """Show edit form for a word."""
    word = db.get_word(dutch)
    if not word:
        return redirect(url_for('index'))

    return render_template('edit.html', word=word)

@app.route('/update/<path:dutch>', methods=['POST'])
def update_word(dutch):
    """Update a word in the database."""
    # Get form data
    word_data = {
        'dutch': request.form.get('dutch'),
        'translation': request.form.get('translation'),
        'definition_nl': request.form.get('definition_nl'),
        'definition_en': request.form.get('definition_en'),
        'pronunciation': request.form.get('pronunciation'),
        'grammar': request.form.get('grammar'),
        'collocations': [x.strip() for x in request.form.get('collocations', '').split('\n') if x.strip()],
        'synonyms': [x.strip() for x in request.form.get('synonyms', '').split('\n') if x.strip()],
        'examples_nl': [x.strip() for x in request.form.get('examples_nl', '').split('\n') if x.strip()],
        'examples_en': [x.strip() for x in request.form.get('examples_en', '').split('\n') if x.strip()],
        'etymology': request.form.get('etymology'),
        'related': [x.strip() for x in request.form.get('related', '').split('\n') if x.strip()]
    }

    # Create Word object
    word = Word(**word_data)

    # Save to database
    db.save_word(word)
    print(f"Updated word: {word.dutch}")

    return redirect(url_for('index'))

def main():
    """CLI entry point for the word viewer."""
    print("Starting Anki GPT Word Viewer...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    main()
