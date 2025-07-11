# AnkiGPT – Telegram bot

Learn Dutch words using Anki flashcards with the help of GPT-4.

## Installation

1. Clone the repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Make sure Anki is running with the AnkiConnect plugin installed

## Setup

The bot requires a few environment variables to be set:

```
OPENAI_API_KEY # ChatGPT API key
TELEGRAM_BOT_TOKEN # Telegram bot token from BotFather
ALLOWED_USER_IDS # Comma-separated list of user ids that can use the bot
```

To set these environment variables in your shell:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
export ALLOWED_USER_IDS="123456789,987654321"
```

## Usage

### Telegram Bot

To start the bot:

```bash
python bot.py
```

### Command Line Interface

To use the CLI:

```bash
python main.py
```

Or for a simpler interface:

```bash
python cli.py
```

## Workflow

1. Send new words, phrases or whole unparsed sentences to Telegram bot.
2. Bot passes the input to ChatGPT and return a json list of word defitions.
3. Bot submits the new words into AnkiConnect API.
4. Bot sends the definitions back to the user.

### Optional

- Bot can send a list of all the words in the Anki deck.
- Bot asks which words to add from the parsed sentence.


## Python modules

### bot.py

- Listens to the user input. All input is treated as words by default.
- Uses main module functions to run the main logic loop of adding words to the Anki deck.
- Returns the added words to the user.

### word.py

- Defines json schema using Pydantic. Its top level object is a list of Word objects. Each Word object has the following fields:
    - Word (in dutch)
    - Translation (in english)
    - Definition (in dutch)
    - Definition (in english)
    - Pronunciation
    - Grammar (add if it's a het or de word. explain the part of speech, parts of the word, like suffix, root, etc, also how the word might change, like tenses, if applicable)
    - Examples (give 2 examples in dutch)
    - Examples (the same examples translated to english)
    - Etymology (match the etymology format of wiktionary, but shorten it a bit)
    - Related (2, 3 examples; always only add related words that are etymologically related; prioritize english, german, russian first)


### chatgpt.py

- Builds a custom propmt with the provided words or sentences.
- Calls ChatGPT Completion API to get the definitions of the words.
- Uses the Word pydantic defitions to parse the json response.
- Return the completion response as a list of Word objects.
- If called from a repl, it should print the json response.

### anki.py

- Connects to AnkiConnect API.
- Adds the words to the Anki deck using the Word pydantic defitions.
- Can list all the words in the deck.
- If called from a repl, it should print the list of words.

### main.py

- Receive the input from the user.
- Calls chatgpt module to get the definitions of the words.
- Calls anki module to add the words to the Anki deck.
- Returns the defitions back.
- If called from a repl, it should return the defitions back too.
