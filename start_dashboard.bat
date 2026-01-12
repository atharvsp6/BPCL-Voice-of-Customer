@echo off
echo ================================================
echo   BPCL Reviews Dashboard - Starting...
echo ================================================
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Launching Streamlit dashboard...
echo Dashboard will open in your browser automatically.
echo.
echo Press Ctrl+C to stop the server.
echo ================================================
echo.

streamlit run 03_dashboard.py

pause
