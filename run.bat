@echo off

cd /d %~dp0

start cmd /k python app.py
cd frontend
start cmd /k npm run dev