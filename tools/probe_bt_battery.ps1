# Hunt for the battery level Windows already knows about a paired BLE keyboard.
#
# BLE HID keyboards expose the standard GATT Battery Service (0x180F) and
# Windows caches the value - that is what the Bluetooth settings page shows.
# This script dumps the PnP property store and the registry parameters of every
# BLE device so we can find which key actually carries the percentage.
#
# ASCII only on purpose: PowerShell 5.1 reads UTF-8-without-BOM as ANSI and
# would mangle any non-ASCII text in here.

$ErrorActionPreference = 'SilentlyContinue'

Write-Output '=== BLE / Bluetooth devices ==='
$all = Get-PnpDevice
$devs = $all | Where-Object {
    $_.InstanceId -like 'BTHLE*' -or
    $_.InstanceId -like 'BTHENUM*' -or
    $_.Class -eq 'Bluetooth'
}
$devs | Select-Object Status, Class, FriendlyName, InstanceId |
    Format-Table -AutoSize | Out-String -Width 220

Write-Output ''
Write-Output '=== property stores (battery-ish keys marked ***) ==='
foreach ($d in $devs) {
    Write-Output ''
    Write-Output ('--- ' + $d.FriendlyName + '  [' + $d.Status + ']')
    Write-Output ('    ' + $d.InstanceId)
    $props = Get-PnpDeviceProperty -InstanceId $d.InstanceId
    if (-not $props) { Write-Output '    (no properties)'; continue }
    foreach ($p in $props) {
        $v = $p.Data
        if ($v -is [byte[]]) { $v = ($v | ForEach-Object { $_.ToString('x2') }) -join ' ' }
        if ($null -eq $v) { $v = '' }
        $line = '{0,-72} {1}' -f $p.KeyName, $v
        if ($p.KeyName -match 'Batter|104EA319|83DA6326|2BD67D8B|Charge') {
            Write-Output ('  *** ' + $line)
        } else {
            Write-Output ('      ' + $line)
        }
    }
}

Write-Output ''
Write-Output '=== registry Device Parameters (BTHLE) ==='
$root = 'HKLM:\SYSTEM\CurrentControlSet\Enum\BTHLE'
if (Test-Path $root) {
    Get-ChildItem $root -Recurse -Depth 2 | ForEach-Object {
        $dp = Join-Path $_.PSPath 'Device Parameters'
        if (Test-Path $dp) {
            Write-Output ('--- ' + $_.PSChildName)
            Get-ItemProperty $dp | Format-List | Out-String -Width 200
        }
    }
} else {
    Write-Output '(no BTHLE key - device may not be paired yet)'
}

Write-Output ''
Write-Output '=== registry values whose name mentions battery ==='
Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Enum' -Recurse -Depth 3 -ErrorAction SilentlyContinue |
    Where-Object { $_.PSChildName -match 'Batter|BATT' } |
    Select-Object -First 40 -ExpandProperty PSPath
