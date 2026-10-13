# 桌面界面依赖

PySide6 6.8.3 / Qt 6.8.3：本应用使用 LGPLv3 许可下的动态库。发行保留动态文件、许可原文和修改/替换 LGPL 库的可能性。

源码来源：
- PySide：[Qt 官方源码](https://code.qt.io/cgit/pyside/pyside-setup.git/?h=6.8.3)
- Qt：[Qt 官方源码](https://code.qt.io/cgit/qt/qtbase.git/?h=v6.8.3)

PyInstaller 仅用于构建，应用目录保留可替换动态依赖。窗口字体使用 Windows 已安装的字体，不随应用再分发。Requests、pyirsdk 等各自许可仍适用；原依赖的元数据与许可随安装包保留。
