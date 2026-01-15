# AnkiGPT

Learn Dutch words using Anki flashcards with AI-powered definitions from OpenAI's GPT models.

**Features:**
- 🤖 **Telegram Bot** - Add words via Telegram
- 🌐 **Web Interface** - Browse, search, edit, and manage words
- 💻 **CLI Tools** - Batch operations and utilities
- 📚 **Rich Definitions** - Etymology, examples, collocations, synonyms, and more
- 🔄 **Anki Sync** - Bidirectional sync with Anki desktop
- 🎨 **Dark Mode** - System-aware theme
- ⚡ **Incremental Search** - Real-time search as you type
- 🔧 **Customizable** - Configure model, effort level, and verbosity
 - 🛡️ **Safe HTML** - Inline-only HTML sanitization when saving; preserves basic tags (b, i, em, strong, u, s, sub, sup, code, br), strips others, and auto-closes broken tags

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Make sure Anki is running with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) plugin installed

## Setup

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your-openai-api-key
TELEGRAM_BOT_TOKEN=your-telegram-bot-token  # Optional, for Telegram bot
ALLOWED_USER_IDS=123456789                   # Optional, for Telegram bot
```

## Usage

### Web Interface

Start the web viewer:

```bash
python web/viewer.py
```

Then open http://127.0.0.1:5000 in your browser.

**Features:**
- Browse and search all words
- Edit word definitions
- Regenerate individual words with AI
- Quick add words from the header
- Incremental search (updates as you type)
- Regeneration queue (batch review and approve changes)
- Dark/light theme toggle
- Sync to/from Anki

### Command Line Interface

Available commands:

```bash
anki-gpt                    # Interactive mode: add words
anki-gpt add                # Interactive mode: add words
anki-gpt import             # Import words from Anki to database
anki-gpt export             # Export words from database to Anki
anki-gpt sync               # Sync all database words to Anki
anki-gpt regenerate         # Regenerate all words without a level (batched, 10 concurrent)
anki-gpt help               # Show help message
```

### Telegram Bot

Start the bot:

```bash
python bot.py
```

Send Dutch words or phrases to the bot, and it will:
1. Generate comprehensive definitions using AI
2. Save to the local database
3. Sync to your Anki deck
4. Send the definitions back to you

## Configuration

### User Settings (Web Interface)

Access settings at `/settings`:
- **Model**: Choose from gpt-5-nano, gpt-5-mini, gpt-5, gpt-5.2, gpt-4o, gpt-4o-mini
- **Effort Level**: minimal, low, medium, high (reasoning effort)
- **Verbosity**: low, medium, high (detail level in definitions)

Settings are persisted per user and apply to all word generation in the web interface.

## Word Schema

Each word includes:
- **dutch** - The Dutch word (normalized)
- **translation** - English translation
- **pronunciation** - IPA notation
- **grammar** - Part of speech, gender (het/de), conjugations, word parts
- **level** - CEFR level (A1, A2, B1, B2, C1, C2)
- **definition_nl** - Dutch definition
- **definition_en** - English definition
- **examples_nl** - Dutch example sentences
- **examples_en** - English translations of examples
- **collocations** - Common word combinations
- **synonyms** - Dutch synonyms
- **related** - Etymologically related words (cross-language)
- **etymology** - Word origin and history
- **tags** - Custom tags

## Architecture

### Key Modules

**word.py**
- Pydantic models for Word and WordList
- JSON schema validation

**chatgpt.py**
- OpenAI API integration
- Uses structured output parsing
- Configurable model, effort, and verbosity

**word_service.py**
- High-level word management API
- CRUD operations with automatic Anki sync
- Database and Anki abstraction layer

**db.py**
- SQLite database management
- Word storage with timestamps and Anki metadata

**anki.py**
- AnkiConnect API integration
- Note creation, updates, and sync

**web/viewer.py**
- Flask web application
- REST API endpoints
- Settings management

**cli.py**
- Command-line interface
- Batch operations (regenerate)
- Interactive word addition

## Database

Words are stored in `words.db` (SQLite):
- **words** table - Word data and metadata
- **anki_words** table - Anki sync information

## Tips

### Regeneration Queue
1. Click regenerate icon on multiple words
2. They queue up in bottom-right floating box
3. Click any queued word to review changes
4. Click "Approve All" to batch-apply all changes


### Batch Regeneration
Run `anki-gpt regenerate` to:
- Regenerate all words without a CEFR level
- Process 10 words concurrently for speed
- Preserve words that already have levels

## Development

The project uses:
- Python 3.13+
- Flask for web interface
- OpenAI API for word generation
- AnkiConnect for Anki integration
- SQLite for local storage
