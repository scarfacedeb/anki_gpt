from pydantic import BaseModel, Field

class Word(BaseModel):
    dutch: str = Field(validation_alias="Word or phrase to define in dutch")
    translation: str
    definition_nl: str
    definition_en: str
    pronunciation: str
    grammar: str
    collocations: list[str]
    examples_nl: list[str]
    examples_en: list[str]
    etymology: str
    related: list[str]

    model_config = {
        "populate_by_name": True
    }

class WordList(BaseModel):
    words: list[Word]
    context: str | None = Field(default=None, validation_alias="Extra context to inform the user")
    
    model_config = {
        "populate_by_name": True
    }

def word_to_html(word: Word) -> str:
    examples = list(zip(word.examples_nl, word.examples_en))
    examples_html = "".join(
        f"{nl} ({en})" for nl, en in examples
    )

    lines = [
        f"<b>{word.dutch}</b>",
        f"<b>Translation:</b> {word.translation}",
        f"<b>Definition:</b> {word.definition_nl} ({word.definition_en})",
        f"<b>Pronunciation:</b> {word.pronunciation}",
        f"<b>Grammar:</b> {word.grammar}",
        f"<b>Collocations:</b> {', '.join(word.collocations)}",
        f"<b>Etymology:</b> {word.etymology}",
        f"<b>Related:</b> {', '.join(word.related)}",
        f"<i>{examples_html}</i>"
    ]

    return "\n".join(lines)
