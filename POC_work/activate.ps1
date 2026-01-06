# PowerShell script to activate the virtual environment
# Usage: .\activate.ps1

if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated!" -ForegroundColor Green
    Write-Host "To deactivate, run: deactivate" -ForegroundColor Yellow
} else {
    Write-Host "Virtual environment not found. Run: python -m venv venv" -ForegroundColor Red
}

