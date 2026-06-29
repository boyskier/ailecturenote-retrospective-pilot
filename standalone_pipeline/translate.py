from dotenv import load_dotenv
import openai
import os
import asyncio
from prompts import get_SYS_PROMPT_translate
import pandas as pd
from logger import log_gpt_request
import config

load_dotenv(config.ENV_FILE)
openai.api_key = os.getenv("OPEN_API_KEY") or os.getenv("OPENAI_API_KEY")

async def translate_text(text, user_id):
    model = "gpt-3.5-turbo"
    messages = [
        {"role": "system", "content": get_SYS_PROMPT_translate()},
        {"role": "user", "content": text},
    ]

    response = await openai.ChatCompletion.acreate(model=model, messages=messages, temperature=0)
    translated_text = response.choices[0].message['content'].strip()
    # Extract token count
    input_tokens = response['usage']['prompt_tokens']  # Weight by attempt count
    output_tokens = response['usage']['completion_tokens']

    log_gpt_request(user_id, model, input_tokens, output_tokens)

    return translated_text

async def translate(row, user_id):
    text_to_translate = row['text']
    translated_text = await translate_text(text_to_translate, user_id)
    return translated_text

async def apply_translate_to_df(pages_df, user_id):
    tasks = [translate(row, user_id) for _, row in pages_df.iterrows()]
    translated_texts = await asyncio.gather(*tasks)
    new_df = pd.DataFrame({'text': translated_texts, 'chunk_id': pages_df['chunk_id']})  # Create new DataFrame
    return new_df
