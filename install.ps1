# Скрипт установки Solana Token Deployer для Windows PowerShell

Write-Host "🚀 Установка Solana Token Deployer" -ForegroundColor Green
Write-Host "=" * 50

# Проверяем версию Python
Write-Host "🐍 Проверка версии Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Найден Python: $pythonVersion" -ForegroundColor Green
    
    # Проверяем минимальную версию (3.8+)
    $version = [regex]::Match($pythonVersion, "(\d+)\.(\d+)").Groups
    $major = [int]$version[1].Value
    $minor = [int]$version[2].Value
    
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
        Write-Host "❌ Требуется Python 3.8 или выше. Текущая версия: $pythonVersion" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Python не найден. Установите Python 3.8+ с https://python.org" -ForegroundColor Red
    exit 1
}

# Создаем виртуальное окружение
Write-Host "📦 Создание виртуального окружения..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "⚠️ Виртуальное окружение уже существует. Удаляем..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "venv"
}

python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка создания виртуального окружения" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Виртуальное окружение создано" -ForegroundColor Green

# Активируем виртуальное окружение
Write-Host "🔧 Активация виртуального окружения..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Обновляем pip
Write-Host "⬆️ Обновление pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Устанавливаем зависимости
Write-Host "📚 Установка зависимостей..." -ForegroundColor Yellow
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка установки зависимостей" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Зависимости установлены" -ForegroundColor Green

# Создаем .env файл из примера
Write-Host "⚙️ Настройка конфигурации..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Создан файл .env из примера" -ForegroundColor Green
    Write-Host "⚠️ Не забудьте настроить API ключи в файле .env" -ForegroundColor Yellow
} else {
    Write-Host "ℹ️ Файл .env уже существует" -ForegroundColor Cyan
}

# Создаем директории для логов и данных
Write-Host "📁 Создание рабочих директорий..." -ForegroundColor Yellow
$dirs = @("logs", "data", "exports", "tokens")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "✅ Создана директория: $dir" -ForegroundColor Green
    }
}

# Проверяем установку Solana CLI (опционально)
Write-Host "🔍 Проверка Solana CLI..." -ForegroundColor Yellow
try {
    $solanaVersion = solana --version 2>&1
    Write-Host "✅ Найден Solana CLI: $solanaVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Solana CLI не найден. Установите с https://docs.solana.com/cli/install-solana-cli-tools" -ForegroundColor Yellow
    Write-Host "   Это опционально, но рекомендуется для работы с кошельками" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Установка завершена успешно!" -ForegroundColor Green
Write-Host "=" * 50

Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Настройте API ключи в файле .env" -ForegroundColor White
Write-Host "2. Настройте параметры в config/settings.yaml" -ForegroundColor White
Write-Host "3. Запустите демонстрацию: python demo.py" -ForegroundColor White
Write-Host "4. Создайте токен: python main.py interactive" -ForegroundColor White

Write-Host ""
Write-Host "📖 Полезные команды:" -ForegroundColor Cyan
Write-Host "• Активация окружения: venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "• Демонстрация: python demo.py" -ForegroundColor White
Write-Host "• Интерактивное создание: python main.py interactive" -ForegroundColor White
Write-Host "• Создание токена: python main.py create --name 'MyToken' --symbol 'MTK'" -ForegroundColor White
Write-Host "• Помощь: python main.py --help" -ForegroundColor White

Write-Host ""
Write-Host "🔗 Документация и поддержка:" -ForegroundColor Cyan
Write-Host "• README.md - основная документация" -ForegroundColor White
Write-Host "• config/settings.yaml - настройки системы" -ForegroundColor White
Write-Host "• .env - переменные окружения и API ключи" -ForegroundColor White

Write-Host ""
Write-Host "⚠️ Важно:" -ForegroundColor Yellow
Write-Host "• Используйте devnet для тестирования" -ForegroundColor White
Write-Host "• Никогда не публикуйте приватные ключи" -ForegroundColor White
Write-Host "• Проверьте все настройки перед созданием токена в mainnet" -ForegroundColor White
