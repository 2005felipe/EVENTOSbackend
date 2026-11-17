# Prepara el backend: crea el entorno virtual DENTRO de esta carpeta e instala las librerías.
# Uso (PowerShell, estando en la carpeta del backend):   .\instalar.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creando entorno virtual .venv ..." -ForegroundColor Cyan
    if (Get-Command py -ErrorAction SilentlyContinue) { py -m venv .venv } else { python -m venv .venv }
}

Write-Host "Instalando librerías (requirements.txt) ..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env"
    Write-Host "Se creó el archivo .env: ábrelo y completa DB_*, JWT_SECRET_KEY y MAIL_*." -ForegroundColor Yellow
}

Write-Host "Comprobando librerías ..." -ForegroundColor Cyan
.\.venv\Scripts\python.exe -c "import fastapi, uvicorn, pandas, openpyxl, fastapi_mail, pwdlib, psycopg2, jwt, dotenv, email_validator; print('Todo instalado correctamente')"

Write-Host ""
Write-Host "Listo. Para arrancar el servidor:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn main:app --reload"
