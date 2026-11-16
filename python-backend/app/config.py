import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory of the python-backend project
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = (BASE_DIR / "ticketbook.db").as_posix()
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_SQLITE_PATH}"

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or DATABASE_URL == "sqlite:///./ticketbook.db":
    DATABASE_URL = DEFAULT_DB_URL

PORT = int(os.getenv("PORT", "8000"))
