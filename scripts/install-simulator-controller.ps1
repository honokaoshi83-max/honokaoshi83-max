param([switch]$OneClick)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
if ($OneClick) {
    $project = Split-Path -Parent $PSScriptRoot
    $ErrorActionPreference = 'Continue'
    & (Join-Path $project '.runtime/python/python.exe') -X utf8 (Join-Path $project 'work/race-voices/install_simulator.py') 2>&1 | Tee-Object -FilePath (Join-Path $project '.runtime/simulator-install.log')
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Add-Type -AssemblyName System.Windows.Forms
        [void][System.Windows.Forms.MessageBox]::Show('组件安装未完成。请打开助手首页的 Simulator Controller 安装引导，查看并重试。', '组件安装')
    }
    exit $code
}
$result = 0

$downloadUrl = 'https://simulatorcontroller.s3.eu-central-1.amazonaws.com/Simulator+Controller.exe'
$installerPath = Join-Path $env:TEMP ("Simulator-Controller-setup-{0}.exe" -f [Guid]::NewGuid().ToString('N'))

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installerPath -UseBasicParsing

    $file = Get-Item -LiteralPath $installerPath
    if ($file.Length -lt 131072) {
        throw '下载文件过小，可能不是有效的安装程序。'
    }

    $stream = [IO.File]::OpenRead($installerPath)
    try {
        $signature = New-Object byte[] 2
        if ($stream.Read($signature, 0, 2) -ne 2 -or $signature[0] -ne 0x4D -or $signature[1] -ne 0x5A) {
            throw '下载文件不是有效的 Windows 安装程序。'
        }
    }
    finally {
        $stream.Dispose()
    }

    $process = Start-Process -FilePath $installerPath -PassThru -Wait
    if ($process.ExitCode -ne 0) {
        throw "Simulator Controller 安装器退出代码：$($process.ExitCode)"
    }
}
catch {
    $result = 1
    Write-Output ('安装失败：' + $_.Exception.Message)
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show(
        "Simulator Controller 未能启动安装。请检查网络后重试，或打开官方安装页：`r`nhttps://github.com/SeriousOldMan/Simulator-Controller/wiki/Installation-%26-Configuration`r`n`r`n详细信息：$($_.Exception.Message)",
        'Simulator Controller 安装',
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
}
finally {
    if (Test-Path -LiteralPath $installerPath) {
        Remove-Item -LiteralPath $installerPath -Force -ErrorAction SilentlyContinue
    }
}
exit $result
