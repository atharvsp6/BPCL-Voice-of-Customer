# BPCL Reviews Dashboard - Quick Start
# =====================================
# Run this script to launch the dashboard

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  BPCL Reviews Dashboard - Starting..." -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "$PSScriptRoot\venv\Scripts\Activate.ps1"

Write-Host ""
Write-Host "Launching Streamlit dashboard..." -ForegroundColor Yellow
Write-Host "Dashboard will open in your browser automatically." -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

streamlit run "$PSScriptRoot\03_dashboard.py"
