$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$voiceRoot=Join-Path $root 'work/race-voices'
$python=Join-Path $root '.runtime/python/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw '运行环境缺失，无法安全识别本目录服务。' }
& $python -X utf8 (Join-Path $voiceRoot 'stop_services.py')
if ($LASTEXITCODE -ne 0) {throw '停止本目录服务失败。'}
