<#
    Avtomatik ishga tushirishni o'chiradi.

        powershell -ExecutionPolicy Bypass -File uninstall-service.ps1

    Agentning o'zi va sozlamalari joyida qoladi — faqat vazifa
    o'chiriladi. Ishlab turgan agent ham to'xtatiladi.
#>

param(
    [string]$TaskName = 'Chop etish agenti'
)

$ErrorActionPreference = 'Stop'

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if (-not $task) {
    Write-Host "Bunday vazifa yo'q: $TaskName"
    return
}

Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false

# Vazifa to'xtasa ham, ishlab turgan Node jarayoni qolishi mumkin
$owner = (Get-NetTCPConnection -LocalPort 7777 -State Listen -ErrorAction SilentlyContinue).OwningProcess

if ($owner) {
    Stop-Process -Id $owner -Force
    Write-Host "Ishlab turgan agent to'xtatildi (PID $owner)"
}

Write-Host "Vazifa o'chirildi: $TaskName"
