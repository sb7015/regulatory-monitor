@echo off
echo ============================================
echo  Regulatory Monitor Agent - Project Setup
echo  Securian Life (NAIC 93742) - TX + CA
echo ============================================
echo.

:: Navigate to D drive
D:
cd \

:: Create project root
if not exist "regulatory_monitor" mkdir regulatory_monitor
cd regulatory_monitor

echo [1/8] Creating folder structure...
mkdir config 2>nul
mkdir data 2>nul
mkdir data\policy_forms 2>nul
mkdir data\policy_forms\securian 2>nul
mkdir data\db 2>nul
mkdir scrapers 2>nul
mkdir agents 2>nul
mkdir scripts 2>nul
mkdir dashboard 2>nul
mkdir dashboard\pages 2>nul
mkdir models 2>nul
mkdir aws 2>nul
echo       Done.

echo [2/8] Initializing uv project...
uv init --no-readme 2>nul
echo       Done.

echo [3/8] Creating .python-version...
echo 3.12 > .python-version
echo       Done.

echo [4/8] Installing dependencies with uv...
uv add anthropic crewai crewai-tools chromadb sqlalchemy requests beautifulsoup4 lxml streamlit plotly pandas python-dotenv
echo       Done.

echo [5/8] Creating __init__.py files...
type nul > config\__init__.py 2>nul
type nul > scrapers\__init__.py 2>nul
type nul > agents\__init__.py 2>nul
type nul > models\__init__.py 2>nul
echo       Done.

echo [6/8] Creating .env file...
echo ANTHROPIC_API_KEY=REPLACE_WITH_YOUR_NEW_KEY > .env
echo       Done. IMPORTANT: Open .env and paste your new API key.

echo [7/8] Creating .gitignore...
(
echo .env
echo .venv/
echo __pycache__/
echo *.pyc
echo data/db/
echo *.db
echo .chroma/
) > .gitignore
echo       Done.

echo [8/8] Verifying installation...
uv run python -c "import anthropic; print('  anthropic OK')"
uv run python -c "import chromadb; print('  chromadb OK')"
uv run python -c "import sqlalchemy; print('  sqlalchemy OK')"
uv run python -c "import requests; print('  requests OK')"
uv run python -c "import bs4; print('  beautifulsoup4 OK')"
uv run python -c "import streamlit; print('  streamlit OK')"
uv run python -c "import plotly; print('  plotly OK')"
uv run python -c "import pandas; print('  pandas OK')"
uv run python -c "import dotenv; print('  python-dotenv OK')"

echo.
echo ============================================
echo  Setup complete!
echo  Project: D:\regulatory_monitor
echo ============================================
echo.
echo  NEXT STEPS:
echo  1. Open .env and replace REPLACE_WITH_YOUR_NEW_KEY with your regenerated Anthropic API key
echo  2. Copy 18 policy files (P01-P11, R01-R07) into data\policy_forms\securian\
echo  3. Open this folder in VS Code: code .
echo  4. Tell Sanjib's Claude: "Step 1 ready, go to Step 2"
echo.
pause
