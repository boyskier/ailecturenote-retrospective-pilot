"""Compare STT models on one audio file, then run the normal pipeline for whisper-1.

Usage:
    python standalone_pipeline/eval_stt_compare.py lecture.m4a
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

import openai
from dotenv import load_dotenv

import audio_processing
import config

USER_ID = 0
STT_COST_PER_MINUTE = 0.006


def _raw_stt_path(audio_path, suffix):
    stem = Path(audio_path).stem
    raw_stt_dir = Path(config.product_path("raw_stt"))
    raw_stt_dir.mkdir(parents=True, exist_ok=True)
    return str(raw_stt_dir / f"{stem}_{suffix}.txt")


def _transcribe(audio_path, model, suffix):
    audio_processing.STT_MODEL = model
    audio_processing.STT_COST_PER_MINUTE = STT_COST_PER_MINUTE

    transcript = audio_processing.process_audio_with_whisper(audio_path, USER_ID)
    output_path = _raw_stt_path(audio_path, suffix)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"raw STT saved: {output_path}")
    return output_path


def _transcribe_with_prompt(audio_path, model, suffix, prompt):
    """Same as _transcribe but passes a prompt to guide transcription style."""
    audio_processing.STT_MODEL = model
    audio_processing.STT_COST_PER_MINUTE = STT_COST_PER_MINUTE

    transcript = audio_processing.process_audio_with_whisper_prompted(audio_path, USER_ID, prompt)
    output_path = _raw_stt_path(audio_path, suffix)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(transcript)

    print(f"raw STT saved: {output_path}")
    return output_path


def _run_default_pipeline(text_path):
    command = [sys.executable, str(config.PIPELINE_ROOT / "run_pipeline.py"), text_path]
    print("\n=== Running AI_LectureNote pipeline for whisper-1 transcript ===")
    subprocess.run(command, cwd=config.REPO_ROOT, check=True)


STT_PROMPT = "의학 강의 녹음입니다. 영어 의학 용어는 영어로 표기합니다."


def run_prompted_only(audio_path):
    """Run only gpt-4o-transcribe with prompt on a given audio file."""
    converted = audio_processing.convert_to_m4a_if_needed(audio_path)
    _transcribe_with_prompt(converted, "gpt-4o-transcribe", "gpt4otranscribe_3min_no_overlap_prompted", STT_PROMPT)


def run_gpt4o_only(audio_path):
    """Run gpt-4o-transcribe unprompted and prompted on a given audio file."""
    converted = audio_processing.convert_to_m4a_if_needed(audio_path)
    _transcribe(converted, "gpt-4o-transcribe", "gpt4otranscribe_3min_no_overlap")
    _transcribe_with_prompt(converted, "gpt-4o-transcribe", "gpt4otranscribe_3min_no_overlap_prompted", STT_PROMPT)


def main():
    parser = argparse.ArgumentParser(
        description="Run whisper-1 and gpt-4o-transcribe STT on one audio file for comparison."
    )
    parser.add_argument("audio_file", help="input audio file path, typically .m4a")
    parser.add_argument(
        "--prompted-only",
        action="store_true",
        help="skip whisper-1 and unprompted gpt-4o-transcribe; only run gpt-4o-transcribe with prompt",
    )
    parser.add_argument(
        "--gpt4o-only",
        action="store_true",
        help="skip whisper-1 and the default pipeline; only run gpt-4o-transcribe unprompted and prompted",
    )
    args = parser.parse_args()

    load_dotenv(config.ENV_FILE)
    openai.api_key = os.getenv("OPEN_API_KEY") or os.getenv("OPENAI_API_KEY")

    audio_path = Path(args.audio_file).expanduser().resolve()
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    if args.prompted_only:
        run_prompted_only(str(audio_path))
        return

    if args.gpt4o_only:
        run_gpt4o_only(str(audio_path))
        return

    converted_audio_path = audio_processing.convert_to_m4a_if_needed(str(audio_path))

    whisper_path = _transcribe(converted_audio_path, "whisper-1", "whisper1")
    _transcribe(converted_audio_path, "gpt-4o-transcribe", "gpt4otranscribe")
    _transcribe_with_prompt(converted_audio_path, "gpt-4o-transcribe", "gpt4otranscribe_prompted", STT_PROMPT)

    _run_default_pipeline(whisper_path)

    stem = Path(converted_audio_path).stem
    englished_path = config.product_path("englished", f"{stem}_whisper1_englished.txt")
    print(f"AI_LectureNote englished result: {englished_path}")


if __name__ == "__main__":
    main()
