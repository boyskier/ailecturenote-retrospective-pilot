import os
import uuid

import openai
from pydub import AudioSegment

import config

openai.api_key = os.getenv("OPEN_API_KEY") or os.getenv("OPENAI_API_KEY")

# STT model. Alternatives: "gpt-4o-transcribe", "gpt-4o-mini-transcribe".
STT_MODEL = "whisper-1"
STT_COST_PER_MINUTE = 0.006  # USD
DEFAULT_CHUNK_MS = 10 * 60 * 1000
GPT4O_TRANSCRIBE_CHUNK_MS = 3 * 60 * 1000
GPT4O_TRANSCRIBE_OVERLAP_MS = 0
SUPPORTED_AUDIO_FORMATS = {"mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"}


def _chunk_settings_for_model(model):
    if model.startswith("gpt-4o") and "transcribe" in model:
        return GPT4O_TRANSCRIBE_CHUNK_MS, GPT4O_TRANSCRIBE_OVERLAP_MS
    return DEFAULT_CHUNK_MS, 0


def _append_segment_text(result_text, segment_text):
    if not segment_text:
        return result_text
    if not result_text:
        return segment_text
    return result_text.rstrip() + "\n\n" + segment_text.lstrip()


def _transcript_text(transcript):
    if isinstance(transcript, dict):
        return transcript["text"]
    return transcript.text


def _transcribe_segment(temp_file_name, prompt=None):
    with open(temp_file_name, "rb") as audio_file:
        if prompt is None:
            return openai.Audio.transcribe(model=STT_MODEL, file=audio_file)
        return openai.Audio.transcribe(model=STT_MODEL, file=audio_file, prompt=prompt)


def _process_audio_segments(filepath, user_id, prompt=None):
    print('Processing audio with STT model:', STT_MODEL, '(with prompt)' if prompt else '')
    audio = AudioSegment.from_file(filepath)
    total_length = len(audio)
    chunk_ms, overlap_ms = _chunk_settings_for_model(STT_MODEL)
    step_ms = chunk_ms - overlap_ms
    num_segments = (max(total_length - overlap_ms, 0) + step_ms - 1) // step_ms
    result_text = ""

    for i in range(num_segments):
        start_time = i * step_ms
        end_time = min(start_time + chunk_ms, total_length)
        segment = audio[start_time:end_time]
        segment_duration = (end_time - start_time) / 1000.0
        temp_file_name = f"temp_segment_{uuid.uuid4()}.mp3"

        print(f"Processing segment {i + 1}/{num_segments} ({start_time} - {end_time})")
        print(f"Exporting segment to {temp_file_name}")
        segment.export(temp_file_name, format="mp3")

        try:
            transcript = _transcribe_segment(temp_file_name, prompt=prompt)
            result_text = _append_segment_text(result_text, _transcript_text(transcript))
        finally:
            if os.path.exists(temp_file_name):
                os.remove(temp_file_name)

        print(f"[stt usage] model={STT_MODEL} duration={segment_duration:.1f}s "
              f"cost=${segment_duration / 60 * STT_COST_PER_MINUTE:.4f}")

    return result_text


def process_audio_with_whisper(filepath, user_id):
    return _process_audio_segments(filepath, user_id)


def process_audio_with_whisper_prompted(filepath, user_id, prompt):
    """Same as process_audio_with_whisper but passes a prompt to each segment."""
    return _process_audio_segments(filepath, user_id, prompt=prompt)


def convert_to_m4a_if_needed(input_file_path):
    input_extension = os.path.splitext(input_file_path)[1][1:].lower()

    if input_extension in SUPPORTED_AUDIO_FORMATS:
        return input_file_path

    output_file_path = os.path.splitext(input_file_path)[0] + ".m4a"
    audio = AudioSegment.from_file(input_file_path)
    audio.export(output_file_path, format="m4a", bitrate="128k")
    return output_file_path
