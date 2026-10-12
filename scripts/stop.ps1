$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$voiceRoot=Join-Path $root 'work/race-voices'
Set-Content -LiteralPath (Join-Path $voiceRoot 'watchdog.stop') -Value 'manual stop'
foreach ($name in @('watchdog.py','telemetry_announcer.py','bridge.py')) {
    $path=Join-Path $voiceRoot $name
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains(('"'+$path+'"')) } | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
}
Write-Host '本目录播报服务已停止。'
