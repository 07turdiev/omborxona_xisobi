<#
    Chop etish agentini kompyuter yoqilganda avtomatik ishga tushiradi.

    Nega haqiqiy Windows xizmati (service) emas:

    1. Xizmat qilish uchun tashqi o'ram kerak (nssm, winsw). Agent esa
       ataylab bog'liqliksiz yozilgan — bitta ham tashqi paket yo'q.
    2. Xizmat SYSTEM seansida ishlaydi. Yorliq printeriga yozish
       `\\127.0.0.1\XP365B` ulashuvi orqali boradi va u foydalanuvchi
       seansida tekshirilgan. SYSTEM ostida ulashuv boshqacha
       hal bo'lishi mumkin.

    Shuning uchun bu yerda **logonda ishga tushadigan rejalashtirilgan
    vazifa** yaratiladi: kassir tizimga kirishi bilan agent ko'tariladi,
    oyna ochilmaydi, xabarlar `agent.log` ga yoziladi.

    Ishga tushirish (administrator shart emas):

        powershell -ExecutionPolicy Bypass -File install-service.ps1

    O'chirish: uninstall-service.ps1
#>

param(
    [string]$TaskName = 'Chop etish agenti'
)

$ErrorActionPreference = 'Stop'

$agentDir = $PSScriptRoot
$launcher = Join-Path $agentDir 'start-hidden.ps1'

if (-not (Test-Path $launcher)) {
    throw "start-hidden.ps1 topilmadi: $launcher"
}

$node = (Get-Command node -ErrorAction SilentlyContinue).Source

if (-not $node) {
    throw 'node topilmadi. Node.js 20 yoki undan yangisini o''rnating: nodejs.org'
}

if (-not (Test-Path (Join-Path $agentDir 'config.json'))) {
    Write-Warning 'config.json yo''q — agent printerlarsiz ishga tushadi. Namuna: config.example.json'
}

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`"" `
    -WorkingDirectory $agentDir

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

# Vazifa uzluksiz ishlaydi: vaqt chegarasi yo'q, uzilsa qayta uriniladi
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description 'Do''kon dasturi uchun chek va yorliq chop etish agenti (127.0.0.1:7777)' `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName

Write-Host "Vazifa yaratildi va ishga tushirildi: $TaskName"
Write-Host "Jurnal: $(Join-Path $agentDir 'agent.log')"
Write-Host 'Tekshirish: http://127.0.0.1:7777/health'
