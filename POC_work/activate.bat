@echo off
REM Batch script to activate the virtual environment
REM Usage: activate.bat

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
    echo Virtual environment activated!
    echo To deactivate, run: deactivate
) else (
    echo Virtual environment not found. Run: python -m venv venv
)

