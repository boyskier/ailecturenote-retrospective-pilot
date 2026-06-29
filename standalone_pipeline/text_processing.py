from dotenv import load_dotenv
from text_processing_utils import *
import os
import config

load_dotenv(config.ENV_FILE)
openai.api_key = os.getenv("OPEN_API_KEY") or os.getenv("OPENAI_API_KEY")


def get_saved_line_count(output_file_path):
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except FileNotFoundError:
        return 0


def to_chunked(original_file_path, output_file_path):
    saved_line_count = get_saved_line_count(output_file_path)

    with open(original_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    joined_text = ''.join([line.strip() for line in lines[saved_line_count:]])
    joined_text = remove_newlines(joined_text)
    paragraphs = split_text_into_chunk(joined_text)

    with open(output_file_path, "a", encoding="utf-8") as f:
        for paragraph in paragraphs:
            f.write(paragraph + '\n')


def to_corrected(original_file_path, output_file_path, user_id):
    saved_line_count = get_saved_line_count(output_file_path)

    with open(original_file_path, "r", encoding="utf-8") as f:
        paragraphed_contents = f.read().split('\n')

    for paragraph in paragraphed_contents[saved_line_count:]:
        if len(paragraph) > 5:
            corrected_paragraph = correct_or_english_text(paragraph, user_id, 'correct')
            corrected_paragraph = corrected_paragraph.replace('\n', '')
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(corrected_paragraph + '\n')


def to_englished(original_file_path, output_file_path, user_id):
    saved_line_count = get_saved_line_count(output_file_path)

    with open(original_file_path, "r", encoding="utf-8") as f:
        corrected_contents = f.read().split('\n')

    for paragraph in corrected_contents[saved_line_count:]:
        if len(paragraph) > 5:
            englished_paragraph = correct_or_english_text(paragraph, user_id, 'english')
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(englished_paragraph + '\n')


def raw_text_to_englished(file_full_path, user_id):
    filename = os.path.basename(file_full_path)
    file_name, file_extension = os.path.splitext(filename)
    chunked_path = config.product_path('chunked', f'{file_name}_chunked{file_extension}')
    corrected_path = config.product_path('corrected', f'{file_name}_corrected{file_extension}')
    englished_path = config.product_path('englished', f'{file_name}_englished{file_extension}')

    print('chunking...')
    to_chunked(file_full_path, chunked_path)
    print('correcting...')
    to_corrected(chunked_path, corrected_path, user_id)
    print('englishing...')
    to_englished(corrected_path, englished_path, user_id)

    return englished_path
