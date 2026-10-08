<#
    Kassa kompyuteriga chop etish agentini o'rnatadi - bitta bosishda.

    Ishga tushirish: `ORNAT.cmd` ni ikki marta bosing. Shu skript
    administrator huquqini o'zi so'raydi (yorliq printerini ulashish
    uchun kerak) va quyidagi ishlarni ketma-ket bajaradi:

        1. Node.js bor-yo'qligini tekshiradi, yo'q bo'lsa o'rnatadi
        2. C:\madlensen tuzilmasini yaratadi va agentni ko'chiradi
        3. Printerlarni topadi, yorliq printerini ulashadi
        4. config.json ni yozadi (eski sozlamalar saqlanadi)
        5. Avtomatik ishga tushishni yoqadi
        6. Sinov cheki va sinov yorlig'ini chiqaradi

    Qayta ishlatish xavfsiz: har qadam o'zidan oldingi holatni
    tekshiradi va bajarilgan ishni takrorlamaydi.

    Qo'lda boshqarish kerak bo'lsa:

        -Root        qayerga o'rnatiladi (standart C:\madlensen)
        -Site        do'kon manzili (agent faqat shu manzilga javob beradi)
        -ReceiptIp   chek printerining IP si; 'usb' deyilsa ulashuv orqali
        -NoTest      sinov chop etishni o'tkazib yuboradi
#>

[CmdletBinding()]
param(
    [string]$Root = 'C:\madlensen',
    [string]$Site = 'https://madlensen.uz',
    [string]$ReceiptIp = '',
    [string]$LabelPrinter = '',
    [string]$TaskUser = '',
    [switch]$NoTest,
    [switch]$NoShortcut
)

$ErrorActionPreference = 'Stop'

# --- Ekranga chiqarish --------------------------------------------------

$script:stepNumber = 0

function Write-Step {
    param([string]$Text)

    $script:stepNumber += 1

    Write-Host ''
    Write-Host "[$script:stepNumber] $Text" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Text)

    Write-Host "    + $Text" -ForegroundColor Green
}

function Write-Note {
    param([string]$Text)

    Write-Host "    . $Text" -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Text)

    Write-Host "    ! $Text" -ForegroundColor Yellow
}

function Write-Bad {
    param([string]$Text)

    Write-Host "    x $Text" -ForegroundColor Red
}

# --- Yordamchilar -------------------------------------------------------

<#
    Portga ulanib ko'radi.

    `Test-NetConnection` ishlamagan manzilda 20 sekundgacha kutadi -
    o'rnatish paytida bu juda uzoq. Shuning uchun to'g'ridan-to'g'ri
    TCP ulanishi va qisqa muddat ishlatiladi.
#>
function Test-Port {
    param(
        [string]$Address,
        [int]$Port,
        [int]$TimeoutMs = 2000
    )

    $client = New-Object System.Net.Sockets.TcpClient

    try {
        $connect = $client.ConnectAsync($Address, $Port)

        if (-not $connect.Wait($TimeoutMs)) { return $false }

        return $client.Connected
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

<# PATH ni registrdan qayta o'qiydi: winget o'rnatgan dastur shu seansda ko'rinmaydi. #>
function Update-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')

    $env:Path = "$machine;$user"
}

<# Node.js ning katta versiya raqami; o'rnatilmagan bo'lsa 0. #>
function Get-NodeMajor {
    $node = Get-Command node -ErrorAction SilentlyContinue

    if (-not $node) { return 0 }

    try {
        $version = (& node --version) -replace '^v', ''

        return [int]($version.Split('.')[0])
    } catch {
        return 0
    }
}

<#
    Ro'yxatdan bittasini tanlashni so'raydi.

    Printer nomi har kompyuterda boshqacha yozilgan bo'ladi (drayver
    versiyasiga qarab "Xprinter XP-365B", "XP-365B", "365B LABEL").
    Taxmin qilgandan ko'ra so'rash ishonchli.
#>
function Select-FromList {
    param(
        [string]$Title,
        [string[]]$Items,
        [string]$Skip = ''
    )

    Write-Host ''
    Write-Host "    $Title" -ForegroundColor White

    for ($i = 0; $i -lt $Items.Count; $i += 1) {
        Write-Host "      $($i + 1)) $($Items[$i])"
    }

    if ($Skip) { Write-Host "      0) $Skip" }

    while ($true) {
        $answer = Read-Host '    Raqamni kiriting'

        if ($Skip -and $answer -eq '0') { return '' }

        $number = 0

        if ([int]::TryParse($answer, [ref]$number) -and $number -ge 1 -and $number -le $Items.Count) {
            return $Items[$number - 1]
        }

        Write-Warn 'Bunday raqam yo''q - qaytadan.'
    }
}

<# Agentga so'rov yuboradi. Origin shart: usiz agent 403 qaytaradi. #>
function Invoke-Agent {
    param(
        [string]$Path,
        [string]$Method = 'GET',
        $Body = $null
    )

    $uri = "http://127.0.0.1:7777$Path"
    $headers = @{ Origin = $Site }

    if ($Method -eq 'GET') {
        return Invoke-RestMethod -Uri $uri -Headers $headers -TimeoutSec 20
    }

    # Satr sifatida yuborilsa PowerShell 5.1 uni ISO-8859-1 ga o'giradi
    # va o'zbekcha harflar buziladi - shuning uchun UTF-8 baytlar
    $json = $Body | ConvertTo-Json -Depth 6 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)

    return Invoke-RestMethod -Uri $uri -Method Post -Headers $headers `
        -ContentType 'application/json' -Body $bytes -TimeoutSec 30
}

# --- 0. Administrator huquqi -------------------------------------------

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal $identity
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host 'Administrator huquqi so''raladi - yorliq printerini ulashish uchun kerak.' -ForegroundColor Yellow

    # Vazifa AYNAN SHU foydalanuvchi uchun yozilishi kerak. UAC boshqa
    # administrator nomidan ko'tarilsa, `$env:USERNAME` o'zgarib ketadi
    # va agent kassir seansida umuman ishga tushmaydi.
    $arguments = @(
        '-NoProfile'
        '-ExecutionPolicy', 'Bypass'
        '-NoExit'
        '-File', "`"$PSCommandPath`""
        '-TaskUser', "`"$env:USERDOMAIN\$env:USERNAME`""
        '-Root', "`"$Root`""
        '-Site', "`"$Site`""
    )

    if ($ReceiptIp) { $arguments += @('-ReceiptIp', "`"$ReceiptIp`"") }
    if ($LabelPrinter) { $arguments += @('-LabelPrinter', "`"$LabelPrinter`"") }
    if ($NoTest) { $arguments += '-NoTest' }
    if ($NoShortcut) { $arguments += '-NoShortcut' }

    # UAC oynasi rad etilsa Start-Process xato ko'taradi. Qizil .NET
    # xatosi o'rniga tushunarli gap chiqsin.
    try {
        Start-Process powershell -Verb RunAs -ArgumentList $arguments
    } catch {
        Write-Host ''
        Write-Host 'Administrator huquqi berilmadi - o''rnatish to''xtadi.' -ForegroundColor Red
        Write-Host 'ORNAT.cmd ni qaytadan bosing va "Ha" ni tanlang.' -ForegroundColor Red
        Write-Host ''

        Read-Host 'Yopish uchun Enter' | Out-Null
    }

    return
}

if (-not $TaskUser) { $TaskUser = "$env:USERDOMAIN\$env:USERNAME" }

Write-Host ''
Write-Host '=====================================================' -ForegroundColor White
Write-Host ' MADLEN SEN - chop etish agentini o''rnatish' -ForegroundColor White
Write-Host '=====================================================' -ForegroundColor White
Write-Host ''
Write-Note "Joy:   $Root"
Write-Note "Sayt:  $Site"
Write-Note "Xodim: $TaskUser"

if ($TaskUser -ne "$env:USERDOMAIN\$env:USERNAME") {
    Write-Warn 'Administrator boshqa hisob nomidan kirgan.'
    Write-Warn "Avtomatik ishga tushish $TaskUser uchun yoziladi."
}

# --- 1. Node.js ---------------------------------------------------------

Write-Step 'Node.js'

$major = Get-NodeMajor

if ($major -eq 0) {
    Update-Path
    $major = Get-NodeMajor
}

if ($major -ge 20) {
    Write-Ok "Node.js v$major o'rnatilgan"
} else {
    if ($major -gt 0) {
        Write-Warn "Node.js v$major juda eski - 20 yoki undan yangisi kerak"
    } else {
        Write-Note 'Node.js topilmadi - winget bilan o''rnatiladi'
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Bad 'winget ham yo''q. Node.js ni qo''lda o''rnating: https://nodejs.org (LTS)'
        Write-Bad 'Keyin shu faylni qaytadan ishga tushiring.'

        return
    }

    Write-Note 'Yuklab olinmoqda, bu bir-ikki daqiqa olishi mumkin...'

    & winget install --id OpenJS.NodeJS.LTS --exact `
        --accept-source-agreements --accept-package-agreements `
        --disable-interactivity | Out-Null

    Update-Path
    $major = Get-NodeMajor

    if ($major -lt 20) {
        Write-Bad 'Node.js o''rnatilmadi. Kompyuterni qayta yuklab, shu faylni yana ishga tushiring.'

        return
    }

    Write-Ok "Node.js v$major o'rnatildi"
}

# --- 2. Papka tuzilmasi -------------------------------------------------

Write-Step 'Papka tuzilmasi'

$agentDir = Join-Path $Root 'agent'
$source = $PSScriptRoot

if (-not (Test-Path $Root)) {
    New-Item -ItemType Directory -Path $Root -Force | Out-Null
    Write-Ok "Yaratildi: $Root"
}

if ($source.TrimEnd('\') -ieq $agentDir.TrimEnd('\')) {
    Write-Ok 'Agent allaqachon o''z joyida'
} else {
    # Sozlama va jurnal ko'chirilmaydi: birinchisi shu kompyuterga
    # tegishli, ikkinchisi oldingi kunlarning xabarlari
    $skip = @('config.json', 'agent.log', 'node_modules')

    if (Test-Path $agentDir) {
        Write-Note 'Eski nusxa almashtiriladi'
    } else {
        New-Item -ItemType Directory -Path $agentDir -Force | Out-Null
    }

    # Har element aniq manzilga ko'chiriladi va avval eskisi o'chadi.
    #
    # `Copy-Item -Destination $agentDir -Recurse` deb yozilsa, nishonda
    # shu nomli papka bor bo'lsa u ICHIGA ko'chadi: `agent\src\src`.
    # Eskisini o'chirish yana bir foyda beradi - oldingi versiyadan
    # qolgan keraksiz fayl ortda qolmaydi.
    Get-ChildItem -Path $source | Where-Object { $skip -notcontains $_.Name } | ForEach-Object {
        $target = Join-Path $agentDir $_.Name

        if (Test-Path $target) { Remove-Item -Path $target -Recurse -Force }

        Copy-Item -Path $_.FullName -Destination $target -Recurse -Force
    }

    Write-Ok "Agent ko'chirildi: $agentDir"
}

# --- 3. Printerlar ------------------------------------------------------

Write-Step 'Printerlar'

$printers = @(Get-Printer | Sort-Object Name)

if (-not $printers.Count) {
    Write-Bad 'Bu kompyuterda birorta printer yo''q.'
    Write-Bad 'Avval drayverlarni o''rnatib printerlarni ulang: docs/hardware.md, 1-bo''lim.'

    return
}

foreach ($printer in $printers) {
    Write-Note $printer.Name
}

# 3.1. Yorliq printeri - USB, ulashuv orqali yoziladi

$labelName = $LabelPrinter

if (-not $labelName) {
    $guess = @($printers | Where-Object { $_.Name -match '365' })

    if ($guess.Count -eq 1) {
        $labelName = $guess[0].Name
        Write-Ok "Yorliq printeri topildi: $labelName"
    } else {
        $labelName = Select-FromList -Title 'Yorliq printeri (XP-365B) qaysi?' `
            -Items ($printers | ForEach-Object { $_.Name }) `
            -Skip 'Yorliq printeri yo''q'
    }
}

$labelShare = ''

if ($labelName) {
    $current = Get-Printer -Name $labelName

    if ($current.Shared -and $current.ShareName) {
        Write-Ok "Ulashuv bor: $($current.ShareName)"
        $labelShare = "\\127.0.0.1\$($current.ShareName)"
    } else {
        Set-Printer -Name $labelName -Shared $true -ShareName 'XP365B'
        Write-Ok 'Ulashildi: XP365B'
        $labelShare = '\\127.0.0.1\XP365B'
    }
} else {
    Write-Warn 'Yorliq printeri sozlanmaydi - shtrix-kod brauzer oynasidan chiqadi'
}

# 3.2. Chek printeri - LAN (tez va ishonchli) yoki USB ulashuvi

$receiptHost = ''
$receiptShare = ''

if ($ReceiptIp -and $ReceiptIp -ne 'usb') {
    $receiptHost = $ReceiptIp
} elseif ($ReceiptIp -eq 'usb') {
    $receiptShare = 'ask'
} else {
    # Tarmoqdagi printerlarning IP si port obyektidan olinadi.
    #
    # Port NOMI bilan cheklanib bo'lmaydi: amalda `192.168.30.30`
    # nomli port `192.168.30.130` ga ishlab turgani uchragan.
    $tcpPorts = @(Get-PrinterPort | Where-Object { $_.PrinterHostAddress })

    $networked = @()

    foreach ($printer in $printers) {
        if ($printer.Name -eq $labelName) { continue }

        $port = $tcpPorts | Where-Object { $_.Name -eq $printer.PortName } | Select-Object -First 1

        if ($port) {
            $networked += [pscustomobject]@{
                Name = $printer.Name
                Address = $port.PrinterHostAddress
            }
        }
    }

    # Nomi chek printeriga o'xshaganlar afzal. Usiz ofisdagi boshqa
    # tarmoq printeri (masalan nusxa ko'chirgich) tanlanib qolardi va
    # unga ESC/POS baytlari yuborilardi.
    $likely = @($networked | Where-Object { $_.Name -match 'Q80|XP-?80|POS|chek|receipt' })

    if ($likely.Count -eq 1) {
        $receiptHost = $likely[0].Address
        Write-Ok "Chek printeri tarmoqda topildi: $($likely[0].Name) -> $receiptHost"
    } else {
        $choices = @()

        $pool = $networked

        if ($likely.Count -gt 1) { $pool = $likely }

        foreach ($item in $pool) {
            $choices += "$($item.Name)  ->  $($item.Address)"
        }

        $choices += 'IP ni qo''lda kiritaman'
        $choices += 'USB bilan ulangan (ulashuv orqali)'

        if ($networked.Count) {
            Write-Note 'Chek printerini aniq tanlash kerak.'
        } else {
            Write-Note 'Tarmoqda chek printeri topilmadi.'
        }

        $picked = Select-FromList -Title 'Chek printeri (XP-Q80AS) qaysi?' -Items $choices

        if ($picked -eq 'USB bilan ulangan (ulashuv orqali)') {
            $receiptShare = 'ask'
        } elseif ($picked -eq 'IP ni qo''lda kiritaman') {
            $answer = Read-Host '    Chek printerining IP si'

            if ($answer) { $receiptHost = $answer.Trim() } else { $receiptShare = 'ask' }
        } else {
            $receiptHost = ($picked -split '->')[-1].Trim()
            Write-Ok "Tanlandi: $receiptHost"
        }
    }
}

if ($receiptHost) {
    if (Test-Port -Address $receiptHost -Port 9100) {
        Write-Ok "$receiptHost`:9100 javob berdi"
    } else {
        Write-Warn "$receiptHost`:9100 javob bermadi - sozlama baribir yoziladi"
        Write-Warn 'Printerni yoqib, tarmoq kabelini tekshiring: docs/hardware.md, 3.3-bo''lim'
    }
}

if ($receiptShare -eq 'ask') {
    $candidates = @($printers | Where-Object { $_.Name -ne $labelName } | ForEach-Object { $_.Name })

    if ($candidates.Count) {
        $receiptName = Select-FromList -Title 'Chek printeri (XP-Q80AS) qaysi?' `
            -Items $candidates -Skip 'Chek printeri yo''q'
    } else {
        $receiptName = ''
    }

    if ($receiptName) {
        $current = Get-Printer -Name $receiptName

        if ($current.Shared -and $current.ShareName) {
            $receiptShare = "\\127.0.0.1\$($current.ShareName)"
            Write-Ok "Ulashuv bor: $($current.ShareName)"
        } else {
            Set-Printer -Name $receiptName -Shared $true -ShareName 'XPQ80AS'
            $receiptShare = '\\127.0.0.1\XPQ80AS'
            Write-Ok 'Ulashildi: XPQ80AS'
        }
    } else {
        $receiptShare = ''
        Write-Warn 'Chek printeri sozlanmaydi - chek brauzer oynasidan chiqadi'
    }
}

# --- 4. config.json ----------------------------------------------------

Write-Step 'Sozlama'

$configPath = Join-Path $Root 'config.json'
$old = $null

if (Test-Path $configPath) {
    try {
        $old = Get-Content -Path $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Note 'Eski config.json o''qildi - sozlangan qiymatlar saqlanadi'
    } catch {
        Write-Warn 'Eski config.json buzuq - yangisi yoziladi'
    }
}

<# Eski fayldagi qiymatni oladi, yo'q bo'lsa standartni qaytaradi. #>
function Get-Old {
    param([string]$Printer, [string]$Key, $Default)

    if (-not $old) { return $Default }
    if (-not $old.printers) { return $Default }

    $node = $old.printers.$Printer

    if (-not $node) { return $Default }
    if ($null -eq $node.$Key) { return $Default }

    return $node.$Key
}

$config = [ordered]@{
    port = 7777
    origins = @($Site)
    codePage = 'cp1252'
    printers = [ordered]@{}
}

if ($receiptHost) {
    $config.printers.receipt = [ordered]@{
        transport = 'tcp'
        host = $receiptHost
        port = 9100
        columns = (Get-Old 'receipt' 'columns' 48)
        cashDrawer = [bool](Get-Old 'receipt' 'cashDrawer' $false)
        feedBeforeCut = 5
        cut = 'full'
        barcodeHeight = 80
        barcodeWidth = 2
    }
} elseif ($receiptShare) {
    $config.printers.receipt = [ordered]@{
        transport = 'windows'
        share = $receiptShare
        columns = (Get-Old 'receipt' 'columns' 48)
        cashDrawer = [bool](Get-Old 'receipt' 'cashDrawer' $false)
        feedBeforeCut = 5
        cut = 'full'
        barcodeHeight = 80
        barcodeWidth = 2
    }
}

if ($labelShare) {
    # Zichlik va tezlik do'konda qo'lda sozlanadi - ustiga yozilmaydi
    $config.printers.label = [ordered]@{
        transport = 'windows'
        share = $labelShare
        density = (Get-Old 'label' 'density' 11)
        speed = (Get-Old 'label' 'speed' 3)
        barcodeHeight = 90
    }
}

# BOM bilan yozilsa Node JSON.parse da yiqiladi - shuning uchun BOM'siz UTF-8
$json = $config | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText($configPath, $json, (New-Object Text.UTF8Encoding $false))

Write-Ok "Yozildi: $configPath"

# --- 5. Avtomatik ishga tushish ----------------------------------------

Write-Step 'Avtomatik ishga tushish'

$installService = Join-Path $agentDir 'install-service.ps1'

& $installService -TaskUser $TaskUser

# --- 6. Tekshirish -----------------------------------------------------

Write-Step 'Tekshirish'

$health = $null

foreach ($attempt in 1..15) {
    try {
        $health = Invoke-Agent -Path '/health'

        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $health) {
    Write-Note 'Vazifa orqali ko''tarilmadi - shu seansda ishga tushiriladi'

    Start-Process powershell -WindowStyle Hidden -ArgumentList @(
        '-NoProfile'
        '-ExecutionPolicy', 'Bypass'
        '-File', "`"$(Join-Path $agentDir 'start-hidden.ps1')`""
    )

    foreach ($attempt in 1..15) {
        try {
            $health = Invoke-Agent -Path '/health'

            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
}

if (-not $health) {
    Write-Bad 'Agent ko''tarilmadi.'
    Write-Bad "Jurnalni ko'ring: $(Join-Path $agentDir 'agent.log')"

    return
}

Write-Ok "Agent ishlayapti (v$($health.version))"

foreach ($printer in $health.printers) {
    if ($printer.responds -eq $true) {
        Write-Ok "$($printer.name): $($printer.target) - javob berdi"
    } elseif ($null -eq $printer.responds) {
        # Windows ulashuviga oldindan so'rov yuborib bo'lmaydi -
        # u faqat haqiqiy chop etishda tekshiriladi
        Write-Note "$($printer.name): $($printer.target) - sinov chop etishda tekshiriladi"
    } else {
        Write-Warn "$($printer.name): $($printer.target) - javob bermadi"
    }
}

# --- 7. Sinov chop etish -----------------------------------------------

if (-not $NoTest) {
    Write-Step 'Sinov chop etish'

    $stamp = Get-Date -Format 'dd.MM.yyyy HH:mm'

    if ($config.printers.receipt) {
        try {
            Invoke-Agent -Path '/receipt' -Method POST -Body @{
                shopName = 'MADLEN SEN'
                dateTime = $stamp
                number = 'SINOV'
                cashier = 'O''rnatish'
                lines = @(
                    @{ name = 'Sinov cheki'; quantity = 1; unitPrice = '0'; lineTotal = '0' }
                )
                total = '0'
                paid = '0'
                change = '0'
            } | Out-Null

            Write-Ok 'Sinov cheki yuborildi - printerdan chiqishi kerak'
        } catch {
            Write-Bad "Chek chiqmadi: $($_.Exception.Message)"
        }
    }

    if ($config.printers.label) {
        try {
            # 478 - O'zbekiston prefiksi, oxirgi raqam nazorat raqami
            Invoke-Agent -Path '/labels' -Method POST -Body @{
                labels = @(
                    @{
                        shopName = 'MADLEN SEN'
                        name = 'Sinov yorligi'
                        variant = 'M / qora'
                        price = '0 so''m'
                        barcode = '4780000000007'
                        quantity = 1
                    }
                )
            } | Out-Null

            Write-Ok 'Sinov yorlig''i yuborildi - skaner bilan o''qib ko''ring'
        } catch {
            Write-Bad "Yorliq chiqmadi: $($_.Exception.Message)"
        }
    }
}

# --- 8. Ish stoliga yorliq ---------------------------------------------

if (-not $NoShortcut) {
    Write-Step 'Ish stoliga yorliq'

    # `.url` tanlandi: u har qanday brauzerda ishlaydi va Chrome
    # qayerga o'rnatilganini bilish shart emas
    $desktop = Join-Path $env:PUBLIC 'Desktop'
    $shortcut = Join-Path $desktop 'Madlen sen.url'

    "[InternetShortcut]`r`nURL=$Site`r`n" |
        Out-File -FilePath $shortcut -Encoding ascii -Force

    Write-Ok "Yaratildi: $shortcut"
}

# --- Xulosa ------------------------------------------------------------

Write-Host ''
Write-Host '=====================================================' -ForegroundColor White
Write-Host ' O''RNATISH TUGADI' -ForegroundColor Green
Write-Host '=====================================================' -ForegroundColor White
Write-Host ''
Write-Host ' Qolgan ishlar:' -ForegroundColor White
Write-Host ''
Write-Host "  1. Ish stolidagi 'Madlen sen' yorlig'ini ochib tizimga kiring."
Write-Host '  2. Sozlamalar -> Qurilmalarni sinash: "Agent ishlayapti" yozuvi'
Write-Host '     va sinov tugmalari ko''rinishi kerak.'
Write-Host '  3. Bitta sinov sotuvi qiling. Chrome''ning chop etish oynasi'
Write-Host '     OCHILMASLIGI kerak.'
Write-Host '  4. Skanerni rus klaviaturasi yoqilgan holda ham sinab ko''ring.'
Write-Host ''
Write-Host "  Sozlama:  $configPath"
Write-Host "  Jurnal:   $(Join-Path $agentDir 'agent.log')"
Write-Host '  Qo''llanma: loyiha papkasidagi docs/ornatish.md'
Write-Host ''
