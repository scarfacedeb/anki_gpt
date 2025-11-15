"""
Simple HTML viewer for browsing the local word database.
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path to import from main package
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from urllib.parse import urlencode
from word import Word
from chatgpt import get_definitions
from user_settings import UserConfig, set_user_config
from word_service import WordService

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
word_service = WordService()

# Set up better model for web interface regeneration (user_id=0)
WEB_USER_ID = 0
web_config = UserConfig(model="gpt-5-mini", effort="medium")
set_user_config(WEB_USER_ID, web_config)

def build_pagination_url(page, query, sort_by, order):
    """Build URL query string for pagination."""
    params = {'page': page, 'sort': sort_by, 'order': order}
    if query:
        params['q'] = query
    return urlencode(params)

# Make the function available in templates
app.jinja_env.globals.update(get_pagination_url=build_pagination_url)

def get_words_with_timestamps(query=None):
    """Get words with their created_at, updated_at timestamps, and Anki sync info."""
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
                SELECT w.*, a.anki_note_id, a.deck_name, a.synced_at, a.sync_count,
                       a.reviews, a.lapses, a.ease_factor, a.interval, a.due
                FROM words w
                LEFT JOIN anki_words a ON w.id = a.word_id
                WHERE w.dutch LIKE ? OR w.translation LIKE ?
                   OR w.definition_nl LIKE ? OR w.definition_en LIKE ?
            """, (search_pattern, search_pattern, search_pattern, search_pattern))
        else:
            cursor.execute("""
                SELECT w.*, a.anki_note_id, a.deck_name, a.synced_at, a.sync_count,
                       a.reviews, a.lapses, a.ease_factor, a.interval, a.due
                FROM words w
                LEFT JOIN anki_words a ON w.id = a.word_id
            """)

        rows = cursor.fetchall()
        for row in rows:
            word = word_service.db._dict_to_word(dict(row))
            created_at = row['created_at']
            updated_at = row['updated_at']

            # Extract Anki sync info
            anki_info = {
                'synced': row['anki_note_id'] is not None,
                'note_id': row['anki_note_id'],
                'deck_name': row['deck_name'],
                'synced_at': row['synced_at'],
                'sync_count': row['sync_count'],
                'reviews': row['reviews'],
                'lapses': row['lapses'],
                'ease_factor': row['ease_factor'],
                'interval': row['interval'],
                'due': row['due']
            }

            words_data.append((word, created_at, updated_at, anki_info))

    return words_data

@app.route('/')
def index():
    """Main page showing all words or search results with pagination."""
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'created_at')  # Default sort by created date
    order = request.args.get('order', 'desc')  # Default newest first
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
    elif sort_by == 'created_at':
        all_words.sort(key=lambda w: w[1] or '', reverse=reverse)

    # Pagination
    total_words = len(all_words)
    total_pages = (total_words + per_page - 1) // per_page  # Ceiling division
    page = min(page, max(1, total_pages))  # Ensure page is within valid range

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    words_data = all_words[start_idx:end_idx]

    # Calculate page range to show (maximum 3 pages)
    page_range = []
    if total_pages <= 3:
        # Show all pages if 3 or fewer
        page_range = list(range(1, total_pages + 1))
    else:
        # Show maximum 3 pages centered around current page
        if page == 1:
            page_range = [1, 2, 3]
        elif page >= total_pages:
            page_range = [total_pages - 2, total_pages - 1, total_pages]
        else:
            page_range = [page - 1, page, page + 1]

    stats = word_service.get_stats()

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
    """Delete a word from the database and Anki."""
    db_deleted, anki_deleted = word_service.delete(dutch)

    if db_deleted:
        logger.info(f"Deleted word from database: {dutch} (Anki: {anki_deleted})")
    else:
        logger.warning(f"Failed to delete word: {dutch}")

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax'):
        if db_deleted:
            stats = word_service.get_stats()
            return jsonify({
                'success': True,
                'stats': stats,
                'deleted_from_anki': anki_deleted
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete word'}), 400

    # Regular form submission - redirect
    return redirect(url_for('index'))

@app.route('/quick-add', methods=['POST'])
def quick_add_word():
    """Quick add a new word using ChatGPT."""
    try:
        data = request.json
        dutch = data.get('dutch', '').strip()

        if not dutch:
            return jsonify({'success': False, 'error': 'No word provided'}), 400

        # Check if word already exists
        if word_service.exists(dutch):
            return jsonify({'success': False, 'error': f'Word "{dutch}" already exists in database'}), 400

        # Generate word data using ChatGPT (uses gpt-5-mini with medium effort)
        result = get_definitions(dutch, user_id=WEB_USER_ID)

        if not result.words or len(result.words) == 0:
            return jsonify({'success': False, 'error': 'Failed to generate word data'}), 500

        # Save the first word (usually there's only one)
        word = result.words[0]
        _, synced = word_service.create(word)
        logger.info(f"Quick added word: {word.dutch} (synced: {synced})")

        return jsonify({
            'success': True,
            'word': word.dutch,
            'word_data': {
                'dutch': word.dutch,
                'translation': word.translation,
                'grammar': word.grammar,
                'pronunciation': word.pronunciation
            }
        })
    except Exception as e:
        logger.error(f"Error in quick add: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats_api():
    """Get database statistics as JSON."""
    stats = word_service.get_stats()
    return jsonify(stats)

@app.route('/edit/<path:dutch>', methods=['GET'])
def edit_word(dutch):
    """Show edit form for a word."""
    word = word_service.get(dutch)
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

    # Save to database and sync to Anki
    _, synced = word_service.update(word)
    logger.info(f"Updated word: {word.dutch} (synced: {synced})")

    return redirect(url_for('index'))

@app.route('/regenerate/<path:dutch>', methods=['POST'])
def regenerate_word(dutch):
    """Regenerate a word using ChatGPT with gpt-5-mini and medium effort."""
    try:
        # Get the current word
        current_word = word_service.get(dutch)
        if not current_word:
            return jsonify({'success': False, 'error': 'Word not found'}), 404

        # Regenerate using ChatGPT (uses gpt-5-mini with medium effort)
        result = get_definitions(dutch, user_id=WEB_USER_ID)

        if not result.words or len(result.words) == 0:
            return jsonify({'success': False, 'error': 'Failed to regenerate word'}), 500

        new_word = result.words[0]

        # Return both old and new word data
        return jsonify({
            'success': True,
            'current': {
                'dutch': current_word.dutch,
                'translation': current_word.translation,
                'definition_nl': current_word.definition_nl,
                'definition_en': current_word.definition_en,
                'pronunciation': current_word.pronunciation,
                'grammar': current_word.grammar,
                'collocations': current_word.collocations,
                'synonyms': current_word.synonyms,
                'examples_nl': current_word.examples_nl,
                'examples_en': current_word.examples_en,
                'etymology': current_word.etymology,
                'related': current_word.related
            },
            'new': {
                'dutch': new_word.dutch,
                'translation': new_word.translation,
                'definition_nl': new_word.definition_nl,
                'definition_en': new_word.definition_en,
                'pronunciation': new_word.pronunciation,
                'grammar': new_word.grammar,
                'collocations': new_word.collocations,
                'synonyms': new_word.synonyms,
                'examples_nl': new_word.examples_nl,
                'examples_en': new_word.examples_en,
                'etymology': new_word.etymology,
                'related': new_word.related
            }
        })
    except Exception as e:
        logger.error(f"Error regenerating word: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/confirm-regenerate/<path:dutch>', methods=['POST'])
def confirm_regenerate(dutch):
    """Confirm and save the regenerated word."""
    try:
        word_data = request.json
        word = Word(**word_data)
        _, synced = word_service.update(word)
        logger.info(f"Confirmed regenerated word: {word.dutch} (synced: {synced})")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error saving regenerated word: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

def main():
    """CLI entry point for the word viewer."""
    # Configure logging for the viewer
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    print("Starting Anki GPT Word Viewer...")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host='127.0.0.1', port=5000)

if __name__ == '__main__':
    main()
