@echo off
cd /d C:\Users\gurra\.gemini\RazorScope\services\api
C:\Users\gurra\anaconda3\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8090
