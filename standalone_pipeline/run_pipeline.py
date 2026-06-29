"""Standalone runner for the historical AI_LectureNote core pipeline.

Usage:
    python standalone_pipeline/run_pipeline.py lecture1.mp3
    python standalone_pipeline/run_pipeline.py lecture1.txt lecture2.txt
    python standalone_pipeline/run_pipeline.py --skip-kg lecture1.mp3
    python standalone_pipeline/run_pipeline.py --kg-only lecture1_englished.txt
    python standalone_pipeline/run_pipeline.py --model gpt-4o lecture1.txt
"""
import argparse
from pathlib import Path
import traceback

import audio_processing
import config
from text_processing import raw_text_to_englished
from knowledge_graph import make_knowledge_graph_from_script

USER_ID = 0

AUDIO_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".mpeg",
    ".mpga",
    ".m4a",
    ".wav",
    ".webm",
}


def _stt_suffix():
    return audio_processing.STT_MODEL.replace("-", "").replace("_", "")


def _raw_stt_path(audio_path):
    stem = Path(audio_path).stem
    return config.product_path("raw_stt", f"{stem}_{_stt_suffix()}.txt")


def _is_audio_file(file_path):
    return Path(file_path).suffix.lower() in AUDIO_EXTENSIONS


def _audio_to_raw_text(file_path):
    audio_path = Path(file_path).expanduser().resolve()
    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    converted_audio_path = audio_processing.convert_to_m4a_if_needed(str(audio_path))
    transcript = audio_processing.process_audio_with_whisper(converted_audio_path, USER_ID)
    output_path = _raw_stt_path(converted_audio_path)

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(transcript)

    print(f"raw STT saved: {output_path}")
    return output_path


def _resolve_text_path(file_path):
    text_path = Path(file_path).expanduser().resolve()
    if not text_path.exists():
        raise FileNotFoundError(text_path)
    return str(text_path)


def _prepare_englished_input(file_path):
    if _is_audio_file(file_path):
        text_path = _audio_to_raw_text(file_path)
    else:
        text_path = _resolve_text_path(file_path)

    englished_path = raw_text_to_englished(text_path, USER_ID)
    print(f"englished file saved: {englished_path}")
    return englished_path


def main():
    parser = argparse.ArgumentParser(
        description="Run the historical AI_LectureNote pipeline on audio or text files."
    )
    parser.add_argument("files", nargs="+", help="input audio files, raw STT .txt files, or Englished .txt files")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="model for KG triple extraction")
    parser.add_argument(
        "--kg-only",
        action="store_true",
        help="skip STT/chunk/correct/Englishing; input files are already Englished",
    )
    parser.add_argument(
        "--skip-kg",
        action="store_true",
        help="run only STT/chunk/correction/English-script rendering",
    )
    parser.add_argument("--chunk-sentence-size", type=int, default=10)
    parser.add_argument("--chunk-sentence-overlap", type=int, default=2)
    args = parser.parse_args()

    if args.kg_only and args.skip_kg:
        parser.error("--kg-only and --skip-kg cannot be used together")

    for file_path in args.files:
        print(f"\n=== Processing: {file_path} ===")
        try:
            if args.kg_only:
                englished_path = _resolve_text_path(file_path)
            else:
                englished_path = _prepare_englished_input(file_path)

            if args.skip_kg:
                continue

            output = make_knowledge_graph_from_script(
                englished_path,
                args.model,
                USER_ID,
                chunk_sentence_size=args.chunk_sentence_size,
                chunk_sentence_overlap=args.chunk_sentence_overlap,
            )
            print(f"knowledge graph saved: {output}")
        except Exception:
            print(f"FAILED: {file_path}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
