import tiktoken
import openai
from logger import log_gpt_request, is_not_billing_error
import time
from prompts import get_SYS_PROMPT_ENGLISHED

encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

def remove_newlines(text):
    print("removed")
    text2 = text.replace("/n", "")
    text3 = text2.replace("니다 ", "니다. ")
    return text3.replace("요 ", "요. ")


def split_text_into_chunk(text, max_length=800):
    paragraphs = []
    start = 0
    end = 0

    while start < len(text):
        # Find the last period within 800 characters
        end = start + max_length
        if end >= len(text):
            end = len(text)
        else:
            while end > start and text[end] not in '.!?':
                end -= 1
            # If a period, question mark, or exclamation mark is found, include the character after it
            end += 1
        if end - start < 100:
            end = start + 700

        paragraph = text[start:end].strip()
        paragraphs.append(paragraph)
        start = end

    return paragraphs


def correct_or_english_text(prompt, user_id, mode):
    if mode == "correct":
        instruction = f"""이상한 부분을 고친 버전을 줘"""
        model = "gpt-3.5-turbo"

    else:  # mode == "english"
        instruction = get_SYS_PROMPT_ENGLISHED()
        model = "gpt-4o"

    messages = [
        {"role": "system", "content": instruction},  # instruction here
        {"role": "user", "content": prompt}
    ]

    max_retries = 5  # Maximum retry attempts
    for attempt in range(max_retries):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            # Extract token count used in response

            input_tokens = response['usage']['prompt_tokens'] * (
                    attempt + 1)  # Weight by attempt count (costs apply to failed requests as well)
            output_tokens = response['usage']['completion_tokens']

            log_gpt_request(user_id, model, input_tokens, output_tokens)

            return response.choices[0].message["content"]
        except Exception as e:
            print(f"Error occurred during API call (attempt {attempt + 1}/{max_retries}): {e}")

            if attempt == max_retries - 1:  # If error occurs even on the last attempt
                if is_not_billing_error(e):
                    input_tokens = 0
                    output_tokens = 0
                    log_gpt_request(user_id, model, input_tokens, output_tokens)
                else:
                    input_tokens = (len(encoding.encode(prompt)) + len(encoding.encode(instruction)) + 11) * (
                            attempt + 1)
                    output_tokens = 0
                    log_gpt_request(user_id, model, input_tokens, output_tokens)

            time.sleep(5)  # Wait for 5 seconds

    return "Error: API call failed, all retries exhausted"
