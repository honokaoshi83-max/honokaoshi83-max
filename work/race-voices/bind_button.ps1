param([switch]$ValidateOnly)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$base=$PSScriptRoot
$python=Join-Path $base 'venv/Scripts/python.exe'
if (!(Test-Path $python)) {$python=Join-Path (Split-Path (Split-Path $base)) '.runtime/python/python.exe'}
$form=New-Object Windows.Forms.Form
$form.Text='方向盘 · 播报按键绑定';$form.Size=New-Object Drawing.Size(610,280)
$form.StartPosition='CenterScreen';$form.Font=New-Object Drawing.Font('Microsoft YaHei',11)
$label=New-Object Windows.Forms.Label;$label.SetBounds(25,20,550,35);$form.Controls.Add($label)
$info=New-Object Windows.Forms.Label;$info.SetBounds(25,65,550,75);$info.Text='点击绑定后，先松开所有按钮，再按下方向盘上的一个按钮。支持控制器前 32 个按钮。';$form.Controls.Add($info)
$bind=New-Object Windows.Forms.Button;$bind.Text='绑定播报按键';$bind.SetBounds(25,155,250,45);$form.Controls.Add($bind)
$cancel=New-Object Windows.Forms.Button;$cancel.Text='取消绑定';$cancel.SetBounds(310,155,250,45);$cancel.Enabled=$false;$form.Controls.Add($cancel)
$script:job=$null
function Refresh-Binding {
    $cfg=Get-Content (Join-Path $base 'status_button_settings.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $label.Text=('当前绑定：控制器 '+$cfg.device+'，按钮 '+$cfg.button)
}
Refresh-Binding
$bind.Add_Click({
    if ($script:job -and !$script:job.HasExited) {return}
    $script:started=Get-Date
    $script:job=Start-Process -FilePath $python -ArgumentList @('-X','utf8',('"'+(Join-Path $base 'button_binding.py')+'"')) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $base 'binding-ui.log') -RedirectStandardError (Join-Path $base 'binding-ui-error.log') -PassThru
    $bind.Enabled=$false;$cancel.Enabled=$true;$info.Text='等待按键……请按下要绑定的按钮（30 秒内）。'
})
$cancel.Add_Click({[IO.File]::WriteAllText((Join-Path $base 'button_binding.cancel'),'cancel')})
$timer=New-Object Windows.Forms.Timer;$timer.Interval=200
$timer.Add_Tick({
    if ($script:job -and $script:job.HasExited) {
        Refresh-Binding
        $info.Text=(Get-Content (Join-Path $base 'binding-ui.log') -Raw -Encoding UTF8 -ErrorAction SilentlyContinue)+(Get-Content (Join-Path $base 'binding-ui-error.log') -Raw -Encoding UTF8 -ErrorAction SilentlyContinue)
        $bind.Enabled=$true;$cancel.Enabled=$false;$script:job=$null
    }
})
$form.Add_FormClosing({if ($script:job -and !$script:job.HasExited) {[IO.File]::WriteAllText((Join-Path $base 'button_binding.cancel'),'cancel')}})
$timer.Start()
try {if ($ValidateOnly) {'按键绑定窗口构建通过'} else {[void]$form.ShowDialog()}} finally {$timer.Stop();$timer.Dispose();$form.Dispose()}
