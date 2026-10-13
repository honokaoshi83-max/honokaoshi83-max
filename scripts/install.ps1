param([ValidateSet('system','gpt-sovits')][string]$Engine='system',[switch]$DownloadVoices,[switch]$NoShortcut)
$ErrorActionPreference='Stop'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$root=Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath (Join-Path $root 'config/offline-bundle.json')) {
    & (Join-Path $PSScriptRoot 'install-offline.ps1') -NoShortcut:$NoShortcut
    exit
}
$runtime=Join-Path $root '.runtime'
$downloads=Join-Path $runtime 'downloads'
$pythonDir=Join-Path $runtime 'python'
New-Item -ItemType Directory -Force -Path $downloads,$pythonDir | Out-Null
if (![Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { throw '仅支持 Windows x64。' }
if ($Engine -eq 'gpt-sovits' -and !$DownloadVoices) { throw '角色音色须从原作者下载，请使用 -DownloadVoices；不随本项目再分发模型。' }
& (Join-Path $PSScriptRoot 'stop.ps1')
function Download-Checked($job) {
    $target=Join-Path $downloads $job.name
    if ((Test-Path -LiteralPath $target) -and (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLower() -eq $job.sha256) { return $target }
    Write-Host ('下载：'+$job.name)
    $partial=$target+'.part'
    Invoke-WebRequest -UseBasicParsing -Uri $job.url -OutFile $partial -TimeoutSec 300
    if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLower() -ne $job.sha256) { throw ('下载校验失败：'+$job.name) }
    Move-Item -LiteralPath $partial -Destination $target -Force
    return $target
}
function Run-Python([string[]]$Arguments) {
    & $script:python @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('安装步骤失败，退出码 '+$LASTEXITCODE) }
}
$bootstrap=Get-Content -LiteralPath (Join-Path $root 'config/bootstrap.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$script:python=Join-Path $pythonDir 'python.exe'
if (!(Test-Path -LiteralPath $script:python)) {
    $zip=Download-Checked $bootstrap[0]
    Expand-Archive -LiteralPath $zip -DestinationPath $pythonDir -Force
}
$pth=Join-Path $pythonDir 'python310._pth'
[IO.File]::WriteAllText($pth,"python310.zip`n.`nLib/site-packages`n../../work/race-voices`nimport site`n",[Text.UTF8Encoding]::new($false))
New-Item -ItemType Directory -Force -Path (Join-Path $pythonDir 'Lib/site-packages') | Out-Null
& $script:python -c 'import importlib.util,sys; sys.exit(0 if importlib.util.find_spec("pip") else 1)'
if ($LASTEXITCODE -ne 0) { Run-Python @((Download-Checked $bootstrap[1]),'--disable-pip-version-check') }
Run-Python @('-m','pip','install','--disable-pip-version-check','-r',(Join-Path $root 'requirements.txt'))
if ($Engine -eq 'gpt-sovits') {
    Run-Python @('-m','pip','install','torch==2.5.1+cpu','torchaudio==2.5.1+cpu','--index-url','https://download.pytorch.org/whl/cpu')
    Run-Python @('-m','pip','install','-r',(Join-Path $root 'requirements-roles.txt'))
    Run-Python @('-X','utf8',(Join-Path $root 'work/race-voices/portable_assets.py'))
}
$local=Join-Path $root 'config/local.json'
$config=@{}
if (Test-Path -LiteralPath $local) { (Get-Content -LiteralPath $local -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties | ForEach-Object {$config[$_.Name]=$_.Value} }
$config['engine']=$Engine
[IO.File]::WriteAllText($local,($config | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
Run-Python @('-X','utf8',(Join-Path $root 'work/race-voices/doctor.py'))
if (!$NoShortcut) {
    $desktop=[Environment]::GetFolderPath('Desktop')
    $shell=New-Object -ComObject WScript.Shell
    $shortcut=$shell.CreateShortcut((Join-Path $desktop 'iracing中文播报助手.lnk'))
    $desktopExe=Join-Path $root 'iracing-assistant.exe'
    if (Test-Path -LiteralPath $desktopExe) {
        $shortcut.TargetPath=$desktopExe
        $shortcut.Arguments='--project-dir "'+$root+'"'
    } else {
        $shortcut.TargetPath='powershell.exe'
        $shortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $root 'scripts/manage.ps1')+'"'
    }
    $shortcut.WorkingDirectory=$root
    $shortcut.Save()
}
Write-Host '安装完成。双击启动.cmd或桌面快捷方式打开管理界面。'
