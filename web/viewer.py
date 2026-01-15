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
from word import TAGS_ALL

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

app = Flask(__name__)
word_service = WordService()

# Web interface user ID
WEB_USER_ID = 0

def build_pagination_url(page, query, sort_by, order):
    """Build URL query string for pagination."""
    params = {'page': page, 'sort': sort_by, 'order': order}
    if query:
        params['q'] = query
    # Preserve current tag filters if present
    try:
        tags_arg = request.args.get('tags', '').strip()
        if tags_arg:
            params['tags'] = tags_arg
    except Exception:
        # request might not be available in some contexts
        pass
    return urlencode(params)

# Make the function available in templates
app.jinja_env.globals.update(get_pagination_url=build_pagination_url)

def get_words_with_timestamps(query=None):
    """Get words with their created_at, updated_at timestamps, Anki sync info, and search priority."""
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
                       a.reviews, a.lapses, a.ease_factor, a.interval, a.due,
                       CASE
                           WHEN w.dutch LIKE ? THEN 1
                           WHEN w.translation LIKE ? THEN 2
                           ELSE 3
                       END as search_priority
                FROM words w
                LEFT JOIN anki_words a ON w.id = a.word_id
                WHERE w.dutch LIKE ? OR w.translation LIKE ?
                   OR w.definition_nl LIKE ? OR w.definition_en LIKE ?
            """, (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
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
            search_priority = row['search_priority'] if query else 0

            # Extract Anki sync info
            anki_info = {
                'id': row['id'],
                'synced': row['synced_at'] is not None,
                'note_id': row['anki_note_id'],
                'synced_at': row['synced_at'],
                'sync_count': row['sync_count'],
                'reviews': row['reviews'],
                'lapses': row['lapses'],
                'ease_factor': row['ease_factor'],
                'interval': row['interval'],
                'due': row['due']
            }

            words_data.append((word, created_at, updated_at, anki_info, search_priority))

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

    # Tag filtering (OR semantics: any selected tag matches)
    raw_tags = request.args.get('tags', '').strip()
    selected_tags = [t for t in raw_tags.split(',') if t]
    if selected_tags:
        selected_lower = {t.lower() for t in selected_tags}
        def has_any_tag(word_obj):
            word_tags = {str(t).lower() for t in (word_obj.tags or [])}
            return not selected_lower.isdisjoint(word_tags)
        all_words = [w for w in all_words if has_any_tag(w[0])]

    # Sort words
    # When searching, use search_priority as primary sort, user's choice as secondary
    # When not searching, only use user's choice
    reverse = (order == 'desc')
    if query:
        # Multi-level sort: first by search_priority (always ascending), then by user's choice
        # To keep priority ascending while allowing user sort to be descending, we sort in two passes
        if sort_by == 'dutch':
            all_words.sort(key=lambda w: w[0].dutch.lower(), reverse=reverse)
            all_words.sort(key=lambda w: w[4])  # Priority always ascending
        elif sort_by == 'translation':
            all_words.sort(key=lambda w: w[0].translation.lower(), reverse=reverse)
            all_words.sort(key=lambda w: w[4])  # Priority always ascending
        elif sort_by == 'created_at':
            all_words.sort(key=lambda w: w[1] or '', reverse=reverse)
            all_words.sort(key=lambda w: w[4])  # Priority always ascending
        elif sort_by == 'level':
            all_words.sort(key=lambda w: (w[0].level == '', w[0].level), reverse=reverse)
            all_words.sort(key=lambda w: w[4])  # Priority always ascending
    else:
        # Normal sorting without search priority
        if sort_by == 'dutch':
            all_words.sort(key=lambda w: w[0].dutch.lower(), reverse=reverse)
        elif sort_by == 'translation':
            all_words.sort(key=lambda w: w[0].translation.lower(), reverse=reverse)
        elif sort_by == 'created_at':
            all_words.sort(key=lambda w: w[1] or '', reverse=reverse)
        elif sort_by == 'level':
            all_words.sort(key=lambda w: (w[0].level == '', w[0].level), reverse=reverse)

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

    tags_all = TAGS_ALL

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
        zip=zip,
        tags_all=tags_all,
        selected_tags=selected_tags
    )

@app.route('/delete/<int:word_id>', methods=['POST'])
def delete_word(word_id):
    """Delete a word from the database and Anki by ID."""
    db_deleted, anki_deleted = word_service.delete_by_id(word_id)

    if db_deleted:
        logger.info(f"Deleted word from database: ID {word_id} (Anki: {anki_deleted})")
    else:
        logger.warning(f"Failed to delete word: ID {word_id}")

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



@app.route('/settings')
def settings():
    """Settings page."""
    from user_settings import get_user_config
    config = get_user_config(WEB_USER_ID)
    stats = word_service.get_stats()
    return render_template('settings.html', config=config, stats=stats)

@app.route('/api/settings', methods=['GET', 'POST'])
def settings_api():
    """Get or update web interface settings."""
    from user_settings import get_user_config, set_user_setting

    if request.method == 'GET':
        config = get_user_config(WEB_USER_ID)
        return jsonify(config.to_dict())

    # POST - update settings
    try:
        data = request.json
        success = True

        for key, value in data.items():
            if not set_user_setting(WEB_USER_ID, key, value):
                success = False
                return jsonify({'success': False, 'error': f'Invalid value for {key}'}), 400

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

import threading

# Global sync status with thread locks
sync_to_anki_lock = threading.Lock()
sync_to_anki_status = {
    'in_progress': False,
    'last_result': None
}

sync_from_anki_lock = threading.Lock()
sync_from_anki_status = {
    'in_progress': False,
    'last_result': None
}

def run_sync_to_anki_in_background():
    """Run sync to Anki in background thread."""
    try:
        result = word_service.sync_all_to_anki()

        with sync_to_anki_lock:
            sync_to_anki_status['last_result'] = result

        logger.info(f"Background sync to Anki completed: {result}")
    except Exception as e:
        logger.error(f"Background sync to Anki failed: {e}", exc_info=True)

        with sync_to_anki_lock:
            sync_to_anki_status['last_result'] = {
                'success': False,
                'error': str(e)
            }
    finally:
        with sync_to_anki_lock:
            sync_to_anki_status['in_progress'] = False

def run_sync_from_anki_in_background():
    """Run sync from Anki in background thread."""
    try:
        from backfill import export_anki_to_db
        success_count, total_count = export_anki_to_db()

        result = {
            'success': True,
            'synced': success_count,
            'failed': total_count - success_count,
            'total': total_count
        }

        with sync_from_anki_lock:
            sync_from_anki_status['last_result'] = result

        logger.info(f"Background sync from Anki completed: {result}")
    except Exception as e:
        logger.error(f"Background sync from Anki failed: {e}", exc_info=True)

        with sync_from_anki_lock:
            sync_from_anki_status['last_result'] = {
                'success': False,
                'error': str(e)
            }
    finally:
        with sync_from_anki_lock:
            sync_from_anki_status['in_progress'] = False

@app.route('/api/sync/to-anki', methods=['POST'])
def sync_to_anki_api():
    """Start async sync of unsynced database words to Anki."""
    with sync_to_anki_lock:
        if sync_to_anki_status['in_progress']:
            return jsonify({
                'success': False,
                'error': 'Sync to Anki already in progress'
            }), 409

        # Mark as in progress before starting thread
        sync_to_anki_status['in_progress'] = True

    # Start sync in background thread (outside lock to avoid blocking)
    sync_thread = threading.Thread(target=run_sync_to_anki_in_background, daemon=True)
    sync_thread.start()

    return jsonify({
        'success': True,
        'message': 'Sync to Anki started in background'
    })

@app.route('/api/sync/to-anki/status', methods=['GET'])
def sync_to_anki_status_api():
    """Get current sync to Anki status."""
    with sync_to_anki_lock:
        return jsonify({
            'in_progress': sync_to_anki_status['in_progress'],
            'last_result': sync_to_anki_status['last_result']
        })

@app.route('/api/sync/from-anki', methods=['POST'])
def sync_from_anki_api():
    """Start async sync from Anki to database."""
    with sync_from_anki_lock:
        if sync_from_anki_status['in_progress']:
            return jsonify({
                'success': False,
                'error': 'Sync from Anki already in progress'
            }), 409

        # Mark as in progress before starting thread
        sync_from_anki_status['in_progress'] = True

    # Start sync in background thread (outside lock to avoid blocking)
    sync_thread = threading.Thread(target=run_sync_from_anki_in_background, daemon=True)
    sync_thread.start()

    return jsonify({
        'success': True,
        'message': 'Sync from Anki started in background'
    })

@app.route('/api/sync/from-anki/status', methods=['GET'])
def sync_from_anki_status_api():
    """Get current sync from Anki status."""
    with sync_from_anki_lock:
        return jsonify({
            'in_progress': sync_from_anki_status['in_progress'],
            'last_result': sync_from_anki_status['last_result']
        })

@app.route('/edit/<int:word_id>', methods=['GET'])
def edit_word(word_id):
    """Show edit form for a word."""
    word = word_service.get_by_id(word_id)
    if not word:
        return redirect(url_for('index'))

    return render_template('edit.html', word=word, word_id=word_id)

@app.route('/update/<int:word_id>', methods=['POST'])
def update_word(word_id):
    """Update a word in the database."""
    # Get form data
    word_data = {
        'dutch': request.form.get('dutch'),
        'translation': request.form.get('translation'),
        'definition_nl': request.form.get('definition_nl'),
        'definition_en': request.form.get('definition_en'),
        'pronunciation': request.form.get('pronunciation'),
        'grammar': request.form.get('grammar'),
        'level': request.form.get('level', ''),
        'collocations': [x.strip() for x in request.form.get('collocations', '').split('\n') if x.strip()],
        'synonyms': [x.strip() for x in request.form.get('synonyms', '').split('\n') if x.strip()],
        'examples_nl': [x.strip() for x in request.form.get('examples_nl', '').split('\n') if x.strip()],
        'examples_en': [x.strip() for x in request.form.get('examples_en', '').split('\n') if x.strip()],
        'etymology': request.form.get('etymology'),
        'related': [x.strip() for x in request.form.get('related', '').split('\n') if x.strip()],
        'tags': [x.strip() for x in request.form.get('tags', '').split('\n') if x.strip()]
    }

    # Create Word object
    word = Word(**word_data)

    # Save to database by ID and sync to Anki
    _, synced = word_service.update_by_id(word_id, word)
    logger.info(f"Updated word by ID: {word.dutch} (ID: {word_id}, synced: {synced})")

    return redirect(url_for('index'))

@app.route('/regenerate/<int:word_id>', methods=['POST'])
def regenerate_word(word_id):
    """Regenerate a word using ChatGPT with gpt-5-mini and medium effort."""
    try:
        # Get the current word
        current_word = word_service.get_by_id(word_id)
        if not current_word:
            return jsonify({'success': False, 'error': 'Word not found'}), 404

        # Regenerate using ChatGPT (uses gpt-5-mini with medium effort)
        result = get_definitions(current_word.dutch, user_id=WEB_USER_ID)

        if not result.words or len(result.words) == 0:
            return jsonify({'success': False, 'error': 'Failed to regenerate word'}), 500

        new_word = result.words[0]

        # Return both old and new word data
        return jsonify({
            'success': True,
            'current': current_word.model_dump(),
            'new': new_word.model_dump()
        })
    except Exception as e:
        logger.error(f"Error regenerating word: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/confirm-regenerate/<int:word_id>', methods=['POST'])
def confirm_regenerate(word_id):
    """Confirm and save the regenerated word."""
    try:
        word_data = request.json
        word = Word(**word_data)
        _, synced = word_service.update_by_id(word_id, word)
        logger.info(f"Confirmed regenerated word by ID: {word.dutch} (ID: {word_id}, synced: {synced})")
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
