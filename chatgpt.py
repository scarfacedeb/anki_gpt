from openai import OpenAI
import os
import logging
from pathlib import Path
from word import Word, WordList
from user_settings import get_user_config

logger = logging.getLogger(__name__)

# Get API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
OPENAI_MODEL_EFFORT = os.getenv("OPENAI_MODEL_EFFORT", "low")

def load_prompt(filename: str) -> str:
    return open(Path(__file__).parent / "prompts" / filename, 'r').read()

GET_DEFINITIONS_PROMPT = load_prompt("get_definitions_prompt.md")

EXTRACT_WORDS_PROMPT = load_prompt("extract_words_prompt.md")

def build_prompt(prompt: str, input_text: str) -> list[dict]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input_text},
    ]

def get_definitions(input_text: str, user_id: int) -> WordList:
    logger.info(f"Input: {input_text}")

    config = get_user_config(user_id)

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.parse(
        model=config.model,
        reasoning={ 'effort': config.effort },
        text_format=WordList,
        instructions=GET_DEFINITIONS_PROMPT,
        input=input_text,
    )

    result = response.output_parsed

    if hasattr(result, 'words') and result.words:
        for word in result.words:
            logger.info(f"Output: {word.dutch} - {word.translation}")

    return result


def extract_words(input_text: str) -> list[str]:
    messages = build_prompt(EXTRACT_WORDS_PROMPT, input_text)
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.responses.create(
        model=OPENAI_MODEL,
        input=messages,
        reasoning={ 'effort': OPENAI_MODEL_EFFORT }
    )

    return response.output_text.split('; ')


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    test_input = "hond kat of vis"
    definitions = get_definitions(test_input)
    print(definitions)
