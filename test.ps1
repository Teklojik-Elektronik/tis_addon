# TIS Home Assistant Addon - Test Script

Write-Host "TIS Addon Test Başlatılıyor..." -ForegroundColor Green
Write-Host ""

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "HATA: Python bulunamadı!" -ForegroundColor Red
    exit 1
}

Write-Host "Python bulundu: $($pythonCmd.Source)" -ForegroundColor Cyan

# Install dependencies
Write-Host "Bağımlılıklar yükleniyor..." -ForegroundColor Yellow
python -m pip install -q aiohttp jinja2

# Run web UI
Write-Host ""
Write-Host "TIS Web UI başlatılıyor..." -ForegroundColor Green
Write-Host "Tarayıcınızda açın: http://localhost:8888" -ForegroundColor Cyan
Write-Host ""
Write-Host "Durdurmak için Ctrl+C yapın" -ForegroundColor Yellow
Write-Host ""

python web_ui.py --gateway 192.168.1.200 --port 6000
