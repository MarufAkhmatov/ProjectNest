# =====================================================================
#  Temur local AI — one-shot setup / rebuild
#  Run:  powershell -ExecutionPolicy Bypass -File ai\setup-temur.ps1
# =====================================================================
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $PSScriptRoot
$ollama = "C:\Users\ASUS\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollama)) { $ollama = "ollama" }

Write-Host "1/3  Pulling base models (Qwen2.5 3B + 7B + 14B + embeddings)..." -ForegroundColor Cyan
& $ollama pull qwen2.5:3b-instruct
& $ollama pull qwen2.5:7b-instruct
& $ollama pull qwen2.5:14b-instruct
& $ollama pull nomic-embed-text

Write-Host "2/3  Building custom models (Turbo + Flash + Pro)..." -ForegroundColor Cyan
& $ollama create temur-turbo -f "$proj\ai\Modelfile.temur-turbo"
& $ollama create temur       -f "$proj\ai\Modelfile.temur"
& $ollama create temur-pro   -f "$proj\ai\Modelfile.temur-pro"

Write-Host "3/3  Building the RAG index over the active dataset..." -ForegroundColor Cyan
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "C:\Users\ASUS\AppData\Local\Programs\Python\Python314\python.exe" }
& $py "$proj\backend\scripts\build_rag.py"

Write-Host "`nDone. Temur is local. Models:" -ForegroundColor Green
& $ollama list
