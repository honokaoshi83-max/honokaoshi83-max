param([switch]$ValidateOnly)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$root=Split-Path -Parent $PSScriptRoot
$python=Join-Path $root '.runtime/python/python.exe'
$form=New-Object Windows.Forms.Form
$form.Text='iracing中文播报助手'
$form.Size=New-Object Drawing.Size(650,560)
$form.StartPosition='CenterScreen'
$form.Font=New-Object Drawing.Font('Microsoft YaHei',10)
$label=New-Object Windows.Forms.Label
$label.Text='本地中文播报；角色音色是可选下载组件，不需要云端 API。'
$label.SetBounds(20,15,600,32);$form.Controls.Add($label)
$output=New-Object Windows.Forms.TextBox
$output.Multiline=$true;$output.ReadOnly=$true;$output.ScrollBars='Vertical'
$output.SetBounds(20,345,590,150);$form.Controls.Add($output)
$script:job=$null
function Run-Job($file,$extra=@()) {
    if ($script:job -and !$script:job.HasExited) { [Windows.Forms.MessageBox]::Show('已有任务执行中，请等待。');return }
    $log=Join-Path $root '.runtime/manage.log';$err=Join-Path $root '.runtime/manage-error.log'
    if (!(Test-Path -LiteralPath (Join-Path $root '.runtime'))) {New-Item -ItemType Directory -Path (Join-Path $root '.runtime') | Out-Null}
    $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $PSScriptRoot $file)+'"'))+$extra
    $script:job=Start-Process powershell.exe -ArgumentList $arguments -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError $err -PassThru
    $output.Text='正在执行，请等待。安装角色组件会下载模型和推理依赖，耗时取决于网络。'
}
function Button($text,$x,$y,$action) {
    $b=New-Object Windows.Forms.Button;$b.Text=$text;$b.SetBounds($x,$y,185,42);$b.Add_Click($action);$form.Controls.Add($b)
}
Button '启动播报' 20 60 {Run-Job 'start.ps1'}
Button '停止播报' 220 60 {Run-Job 'stop.ps1'}
Button '环境诊断' 420 60 {Run-Job 'task.ps1' @('-Task','doctor')}
Button '接入 Simulator Controller' 20 112 {Run-Job 'task.ps1' @('-Task','configure')}
Button '打开官方安装页面' 220 112 {Start-Process 'https://github.com/SeriousOldMan/Simulator-Controller/releases'}
Button '打开说明' 420 112 {Start-Process (Join-Path $root 'docs/INSTALL.md')}
Button '安装角色音色（大型下载）' 20 164 {Run-Job 'install.ps1' @('-Engine','gpt-sovits','-DownloadVoices','-NoShortcut')}
Button '切回系统中文音色' 220 164 {Run-Job 'install.ps1' @('-Engine','system','-NoShortcut')}
Button '补齐固定提示缓存' 420 164 {Run-Job 'task.ps1' @('-Task','cache')}
$controls=@{}
foreach ($item in @(@('device','控制器编号',1,16,20),@('button','PS 按钮编号',1,32,220),@('port','本机端口',1024,65535,420))) {
    $title=New-Object Windows.Forms.Label;$title.Text=$item[1];$title.SetBounds($item[4],228,185,25);$form.Controls.Add($title)
    $number=New-Object Windows.Forms.NumericUpDown;$number.Minimum=$item[2];$number.Maximum=$item[3];$number.SetBounds($item[4],255,185,30)
    $controls[$item[0]]=$number;$form.Controls.Add($number)
}
$controls.device.Value=1;$controls.button.Value=25;$controls.port.Value=9881
$bindingFile=Join-Path $root 'work/race-voices/status_button_settings.json'
$binding=Get-Content -LiteralPath $bindingFile -Raw -Encoding UTF8 | ConvertFrom-Json
$controls.device.Value=$binding.device;$controls.button.Value=$binding.button
$localFile=Join-Path $root 'config/local.json'
if (Test-Path -LiteralPath $localFile) {$lc=Get-Content -LiteralPath $localFile -Raw -Encoding UTF8 | ConvertFrom-Json;if ($lc.port) {$controls.port.Value=$lc.port}}
Button '保存按键与端口' 20 295 {
    if ($script:job -and !$script:job.HasExited) {return}
    & (Join-Path $PSScriptRoot 'stop.ps1')
    $newBinding=@{device=[int]$controls.device.Value;button=[int]$controls.button.Value;cooldown_seconds=8}
    [IO.File]::WriteAllText($bindingFile,($newBinding | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    $local=@{};if (Test-Path -LiteralPath $localFile) {(Get-Content -LiteralPath $localFile -Raw -Encoding UTF8 | ConvertFrom-Json).PSObject.Properties | ForEach-Object {$local[$_.Name]=$_.Value}}
    $local.port=[int]$controls.port.Value
    [IO.File]::WriteAllText($localFile,($local | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    $output.Text='已保存。请重新启动播报；端口变更后重新接入 Simulator Controller。'
}
Button '检测控制器' 220 295 {Run-Job 'task.ps1' @('-Task','buttons')}
Button '测试中文声音' 420 295 {Run-Job 'task.ps1' @('-Task','speech')}
$timer=New-Object Windows.Forms.Timer;$timer.Interval=1000
$timer.Add_Tick({
    if ($script:job -and $script:job.HasExited) {
        $log=Join-Path $root '.runtime/manage.log';$err=Join-Path $root '.runtime/manage-error.log'
        $output.Text=(Get-Content -LiteralPath $log -Raw -ErrorAction SilentlyContinue)+(Get-Content -LiteralPath $err -Raw -ErrorAction SilentlyContinue)
        if ($script:job.ExitCode -ne 0) {$output.Text+='任务未完成，请查看以上信息。'}
        $script:job=$null
    }
})
$timer.Start()
try {if ($ValidateOnly) {Write-Output '管理界面控件构建通过'} else {[void]$form.ShowDialog()}} finally {$timer.Stop();$timer.Dispose();$form.Dispose()}
