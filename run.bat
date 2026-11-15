@echo off

cd /d %~dp0

call .venv\Scripts\activate.bat
start cmd /k python app.py
cd frontend
start cmd /k npm run dev