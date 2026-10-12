param([ValidateSet('doctor','configure','cache','buttons','speech')][string]$Task)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$python=Join-Path $root '.runtime/python/python.exe'
if (!(Test-Path -LiteralPath $python)) {throw '请先完成安装。'}
$script=switch($Task) {'doctor' {'doctor.py'} 'configure' {'setup_simulator.py'} 'cache' {'warm_cache.py'} 'buttons' {'button_info.py'} 'speech' {'speech_test.py'}}
& $python -X utf8 (Join-Path $root ('work/race-voices/'+$script))
if ($LASTEXITCODE -ne 0) {exit $LASTEXITCODE}
