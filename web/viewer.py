"""
Simple HTML viewer for browsing the local word database.
"""
import sys
from pathlib import Path

# Add parent directory to path to import from main package
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
from db import WordDatabase
from word import Word

# Load environment variables
load_dotenv()

app = Flask(__name__)
db = WordDatabase()

@app.route('/')
def index():
    """Main page showing all words or search results."""
    query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'dutch')  # Default sort by dutch word
    order = request.args.get('order', 'asc')  # Default ascending

    if query:
        words = db.search_words(query)
    else:
        words = db.get_all_words()

    # Sort words
    reverse = (order == 'desc')
    if sort_by == 'dutch':
        words.sort(key=lambda w: w.dutch.lower(), reverse=reverse)
    elif sort_by == 'translation':
        words.sort(key=lambda w: w.translation.lower(), reverse=reverse)
    elif sort_by == 'grammar':
        words.sort(key=lambda w: w.grammar.lower(), reverse=reverse)

    stats = db.get_stats()

    return render_template(
        'index.html',
        words=words,
        stats=stats,
        query=query,
        sort_by=sort_by,
        order=order,
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
