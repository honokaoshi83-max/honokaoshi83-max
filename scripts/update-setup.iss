#ifndef PatchDir
  #error PatchDir must contain patch.zip and apply_update.py
#endif
#ifndef FromVersion
  #define FromVersion "0.2.4"
#endif
#ifndef ToVersion
  #define ToVersion "0.2.6"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist\updates"
#endif
[Setup]
AppName=iracing中文播报助手 增量更新
AppVersion={#ToVersion}
DefaultDirName={code:InstalledPath}
DisableProgramGroupPage=yes
UsePreviousAppDir=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=no
CreateUninstallRegKey=no
UpdateUninstallLogAppName=no
DirExistsWarning=no
OutputDir={#OutputDir}
OutputBaseFilename=iracing-chinese-assistant-{#ToVersion}-update-from-{#FromVersion}
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
SetupLogging=yes
[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
[Files]
Source: "{#PatchDir}\patch.zip"; Flags: dontcopy
Source: "{#PatchDir}\apply_update.py"; Flags: dontcopy
[Run]
Filename: "{app}\iracing-assistant.exe"; Description: "启动新版播报助手"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
[Code]
var Extracted: Boolean;
function InstalledPath(Param: String): String;
begin
  if not RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C6EF8023-4883-4F24-A134-043E8D091F09}_is1', 'InstallLocation', Result) then
    Result := ExpandConstant('{localappdata}\Programs\iRacingChineseAssistant');
end;
function RunPatch(CheckOnly: Boolean): String;
var Args, Report: String; Text: AnsiString; Code: Integer;
begin
  Result := '';
  if not Extracted then begin ExtractTemporaryFile('patch.zip'); ExtractTemporaryFile('apply_update.py'); Extracted := True; end;
  Report := ExpandConstant('{tmp}\update-result.txt');
  Args := '-X utf8 ' + AddQuotes(ExpandConstant('{tmp}\apply_update.py')) + ' --target ' + AddQuotes(ExpandConstant('{app}')) + ' --bundle ' + AddQuotes(ExpandConstant('{tmp}\patch.zip')) + ' --result-file ' + AddQuotes(Report);
  if CheckOnly then Args := Args + ' --check'
  else Args := Args + ' --wait-pid ' + ExpandConstant('{param:WAITPID|0}');
  if not Exec(ExpandConstant('{app}\.runtime\python\python.exe'), Args, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code) then
    Result := '无法启动该目录的运行环境，请选择原安装目录。'
  else if Code <> 0 then begin
    if LoadStringFromFile(Report, Text) then Result := UTF8Decode(Text) else Result := '更新未完成，请检查原安装目录和可用磁盘空间。';
  end;
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin Result := RunPatch(True); end;
procedure CurStepChanged(CurStep: TSetupStep);
var ErrorText: String;
begin
  if CurStep = ssInstall then begin
    WizardForm.StatusLabel.Caption := '正在备份并更新程序，请稍候……';
    ErrorText := RunPatch(False);
    if ErrorText <> '' then RaiseException(ErrorText);
  end;
end;
procedure InitializeWizard();
begin
  WizardForm.SelectDirLabel.Caption := '请选择已安装的 {#FromVersion} 播报助手目录。无需重装模型；已有配置和缓存保留。';
  WizardForm.FinishedLabel.Caption := '程序更新已完成。可以启动新版助手，之后从界面左下角“检查更新”获取后续版本。';
end;
