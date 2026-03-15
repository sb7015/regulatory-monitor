import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
POLICY_FORMS_DIR = DATA_DIR / "policy_forms" / "securian"
DB_DIR = DATA_DIR / "db"
CHROMA_DIR = DB_DIR / "chroma"

DB_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "not-needed-for-dashboard")

CLAUDE_MODEL = "claude-sonnet-4-20250514"

SQLITE_PATH = DB_DIR / "regulatory_monitor.db"
DATABASE_URL = f"sqlite:///{SQLITE_PATH}"

FR_BASE_URL = "https://www.federalregister.gov/api/v1"
FR_ARTICLES_URL = f"{FR_BASE_URL}/documents.json"
FR_DATE_START = "2021-03-15"
FR_DATE_END = "2026-03-15"
FR_PER_PAGE = 100

TDI_BASE_URL = "https://www.tdi.texas.gov/bulletins"
TDI_LIFE_URL = f"{TDI_BASE_URL}/Life.html"

CDI_BULLETINS_URL = "https://www.insurance.ca.gov/0250-insurers/0300-insurers/0200-bulletins/bulletin-notices-commiss-opinion/bulletins.cfm"

OFAC_SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
OFAC_SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

CHROMA_PERSIST_DIR = str(CHROMA_DIR)

STREAMLIT_PAGE_TITLE = "Regulatory Change Monitor — Securian Life (93742)"
STREAMLIT_PAGE_ICON = "🏛️"