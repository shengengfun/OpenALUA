param([string]$Path, [string]$Pattern = '.')
$ErrorActionPreference = 'Stop'
$bytes = [IO.File]::ReadAllBytes($Path)

# ASCII strings
$ascii = New-Object System.Text.StringBuilder
$cur = New-Object System.Text.StringBuilder
foreach ($b in $bytes) {
    if ($b -ge 32 -and $b -le 126) { [void]$cur.Append([char]$b) }
    else {
        if ($cur.Length -ge 5) { [void]$ascii.Append($cur.ToString()).Append("`n") }
        [void]$cur.Clear()
    }
}
if ($cur.Length -ge 5) { [void]$ascii.Append($cur.ToString()) }

# UTF16LE strings
$u16 = New-Object System.Text.StringBuilder
$cur2 = New-Object System.Text.StringBuilder
for ($i = 0; $i -lt $bytes.Length - 1; $i += 2) {
    $lo = $bytes[$i]; $hi = $bytes[$i + 1]
    if ($hi -eq 0 -and $lo -ge 32 -and $lo -le 126) { [void]$cur2.Append([char]$lo) }
    else {
        if ($cur2.Length -ge 5) { [void]$u16.Append($cur2.ToString()).Append("`n") }
        [void]$cur2.Clear()
    }
}
if ($cur2.Length -ge 5) { [void]$u16.Append($cur2.ToString()) }

Write-Output "===== ASCII MATCHES ====="
$ascii.ToString() -split "`n" | Where-Object { $_ -match $Pattern } | Sort-Object -Unique | ForEach-Object { $_ }
Write-Output "===== UTF16 MATCHES ====="
$u16.ToString() -split "`n" | Where-Object { $_ -match $Pattern } | Sort-Object -Unique | ForEach-Object { $_ }
