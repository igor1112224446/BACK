@echo off
cd /d %~dp0
start http://localhost:8000
python -m uvicorn app:app --port 8000
