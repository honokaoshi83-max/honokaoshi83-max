# 0.2.6 本地安装与升级

新设备：运行`iracing-chinese-assistant-0.2.6-setup.exe`，同名`setup-1.bin`必须在同一目录。完整安装包含Python、CPU PyTorch、GPT-SoVITS和默认双音色；Simulator Controller仍通过引导联网安装。

已有0.2.4：从托盘退出旧界面，运行`iracing-chinese-assistant-0.2.6-update-from-0.2.4.exe`，选择原安装目录，直接升级到0.2.6。

已有0.2.5：使用`iracing-chinese-assistant-0.2.6-update-from-0.2.5.exe`。不要选择新建空目录，更新器需要复用原安装环境。

升级保留原有按键、音量、自定义音色和缓存，备份放在安装目录`.updates`。新版左侧栏和托盘均有“检查更新”，后续可联网读取正式版本并下载匹配的增量包。GitHub尚未发布本版时，检查不会向其他用户提供本地构建。

更新前退出驾驶会话并结束其他后台任务。写入失败会恢复旧文件；若出现磁盘／权限问题，按错误提示保留备份。实际另一设备验收仍待进行。
