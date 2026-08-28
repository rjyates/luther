$ErrorActionPreference = 'Stop'

if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    Write-Host 'Luther is not installed yet. Run .\install.ps1 first.' -ForegroundColor Yellow
    exit 1
}

$process = Start-Process 'http://127.0.0.1:8000' -PassThru
& .\.venv\Scripts\python.exe -m uvicorn luther.main:app --host 127.0.0.1 --port 8000

