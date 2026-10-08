<#
    Chop etish agentini kompyuter yoqilganda avtomatik ishga tushiradi.

    Nega haqiqiy Windows xizmati (service) emas:

    1. Xizmat qilish uchun tashqi o'ram kerak (nssm, winsw). Agent esa
       ataylab bog'liqliksiz yozilgan - bitta ham tashqi paket yo'q.
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
    [string]$TaskName = 'Chop etish agenti',

    # Vazifa kim uchun yoziladi. Standart - hozirgi foydalanuvchi.
    #
    # `install.ps1` buni ataylab uzatadi: UAC boshqa administrator
    # nomidan ko'tarilgan bo'lsa, `$env:USERNAME` o'zgarib ketadi va
    # vazifa kassir emas, administrator kirganda ishga tushadigan
    # bo'lib qolardi - ya'ni agent kassa seansida umuman ko'tarilmaydi.
    [string]$TaskUser = ''
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
    Write-Warning 'config.json yo''q - agent printerlarsiz ishga tushadi. Namuna: config.example.json'
}

$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$launcher`"" `
    -WorkingDirectory $agentDir

if (-not $TaskUser) { $TaskUser = "$env:USERDOMAIN\$env:USERNAME" }

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $TaskUser

# Kirishdan tashqari har 5 daqiqada ham uriniladi.
#
# Nega: agent qandaydir sababga ko'ra to'xtasa (jarayon o'ldirildi,
# printer drayveri yiqitdi), faqat kirish tetigida u keyingi ertagacha
# o'lik qolardi - kassir esa kun bo'yi brauzer oynasini yopib o'tirardi.
# `IgnoreNew` tufayli agent ishlab turganda takroriy urinish e'tiborsiz
# qoladi, ya'ni ikkinchi nusxa ko'tarilmaydi.
$repeat = New-ScheduledTaskTrigger `
    -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5)

$trigger.Repetition = $repeat.Repetition

# Vazifa uzluksiz ishlaydi: vaqt chegarasi yo'q, uzilsa qayta uriniladi
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

# Agent kassirning o'z seansida ishlashi kerak: yorliq printeri
# `\\127.0.0.1\XP365B` ulashuvi orqali yoziladi va u foydalanuvchi
# seansida hal bo'ladi. `Limited` - ortiqcha huquq berilmaydi.
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $TaskUser `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $taskPrincipal `
    -Description 'Do''kon dasturi uchun chek va yorliq chop etish agenti (127.0.0.1:7777)' `
    -Force | Out-Null

# Boshqa foydalanuvchi uchun yozilgan vazifa u kirmaguncha
# ko'tarilmaydi - bu xato emas, shuning uchun to'xtatmaymiz.
try {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Vazifa yaratildi va ishga tushirildi: $TaskName"
} catch {
    Write-Host "Vazifa yaratildi: $TaskName"
    Write-Warning "Hozir ishga tushmadi - $TaskUser kompyuterga kirganda ko'tariladi."
}

Write-Host "Jurnal: $(Join-Path $agentDir 'agent.log')"
Write-Host 'Tekshirish: http://127.0.0.1:7777/health'
