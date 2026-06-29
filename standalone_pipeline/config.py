# Standalone configuration (replaces Flask current_app.config).
from pathlib import Path

from dotenv import load_dotenv

PIPELINE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PIPELINE_ROOT.parent
PROJECT_ROOT = str(PIPELINE_ROOT)
ENV_FILE = REPO_ROOT / ".env"

PRODUCTS_DIR = PIPELINE_ROOT / "products"
DATA_DIR = PIPELINE_ROOT / "data"

OUTPUT_DIRS = [
    PRODUCTS_DIR / "raw_stt",
    PRODUCTS_DIR / "chunked",
    PRODUCTS_DIR / "corrected",
    PRODUCTS_DIR / "englished",
    PRODUCTS_DIR / "knowledge_graph",
]

load_dotenv(ENV_FILE)

for directory in OUTPUT_DIRS:
    directory.mkdir(parents=True, exist_ok=True)


def product_path(*parts):
    return str(PRODUCTS_DIR.joinpath(*parts))
