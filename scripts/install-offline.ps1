param([switch]$NoShortcut)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$python=Join-Path $root '.runtime/python/python.exe'
if (!(Test-Path -LiteralPath $python)) {throw '完整运行环境缺失，请重新运行 Setup 安装程序。'}
& $python -X utf8 (Join-Path $root 'work/race-voices/doctor.py')
if ($LASTEXITCODE -ne 0) {throw '离线组件检查未通过。'}
if (!$NoShortcut) {
    $shell=New-Object -ComObject WScript.Shell
    $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'iracing中文播报助手.lnk'))
    $shortcut.TargetPath=Join-Path $root 'iracing-assistant.exe'
    $shortcut.WorkingDirectory=$root
    $shortcut.Save()
}
Write-Host '离线安装完成。无需安装 Python，无需下载默认音色。'
