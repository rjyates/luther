$ErrorActionPreference = 'Stop'

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host 'Python is required. Install Python 3.12 from https://www.python.org/downloads/ and select "Add Python to PATH", then run this script again.' -ForegroundColor Yellow
    exit 1
}

py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ''
Write-Host 'Luther is installed. Run .\start.ps1 to open it.' -ForegroundColor Green
Write-Host 'Optional local AI: install Ollama from https://ollama.com and run: ollama pull qwen3:8b'

