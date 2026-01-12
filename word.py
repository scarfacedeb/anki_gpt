from pydantic import BaseModel, Field

class Word(BaseModel):
    dutch: str = Field(validation_alias="Word or phrase to define in dutch")
    translation: str
    definition_nl: str
    definition_en: str
    pronunciation: str
    grammar: str
    collocations: list[str]
    synonyms: list[str]
    examples_nl: list[str]
    examples_en: list[str]
    etymology: str
    related: list[str]
    level: str = Field(
        default="",
        description="CEFR difficulty level for Dutch learners. Examples: A1 (beginner), A2 (elementary), B1 (intermediate), B2 (upper-intermediate), C1 (advanced), C2 (proficient)"
    )

    model_config = {
        "populate_by_name": True
    }

class WordList(BaseModel):
    words: list[Word]
    context: str | None = Field(default=None, validation_alias="Extra context to inform the user")
    
    model_config = {
        "populate_by_name": True
    }

def word_to_anki(word: Word) -> dict:
    """Convert a Word object to Anki fields dictionary."""
    return {
        "Word": word.dutch,
        "Translation": word.translation,
        "Definition": word.definition_nl,
        "Definition (eng)": word.definition_en,
        "Pronunciation": word.pronunciation,
        "Grammar": word.grammar,
        "Collocations": "\n".join(word.collocations),
        "Synonyms": "\n".join(word.synonyms),
        "Examples": "\n".join(word.examples_nl),
        "Examples (eng)": "\n".join(word.examples_en),
        "Etymology": word.etymology,
        "Related": "\n".join(word.related)
    }

def word_to_html(word: Word) -> str:
    examples = list(zip(word.examples_nl, word.examples_en))
    examples_html = "".join(
        f"{nl} ({en})" for nl, en in examples
    )

    lines = [
        f"<b>{word.dutch}</b>\n",
        f"<b>Translation:</b> {word.translation}",
        f"<b>Etymology:</b> {word.etymology}",
        f"<b>Grammar:</b> {word.grammar}",
        f"<b>Pronunciation:</b> {word.pronunciation}",
        f"<b>Collocations:</b> {', '.join(word.collocations)}",
        f"<b>Synonyms:</b> {', '.join(word.synonyms)}",
        f"<b>Related:</b> {', '.join(word.related)}",
        f"<b>Definition:</b> {word.definition_nl} ",
        f"<b>Definition EN:</b> {word.definition_en} ",
        f"<b>Examples:</b><i>{examples_html}</i>"
    ]

    return "\n".join(lines)
