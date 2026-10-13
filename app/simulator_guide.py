"""Guided installation, upstream setup and speech integration."""
import json
from datetime import datetime
from PySide6.QtCore import QProcess, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QFileDialog, QMessageBox
from backend import atomic_json
from simulator_status import inspect_simulator, GUIDE_URL

class SimulatorGuide(QDialog):
    def __init__(self, backend, parent=None):
        super().__init__(parent)
        self.backend = backend; self.job = None; self.pending_output = ''; self.task_active = False
        self.log_path = backend.project / 'logs/simulator-install.log'
        self.progress_timer = QTimer(self); self.progress_timer.setInterval(900)
        self.progress_timer.timeout.connect(self.advance_progress)
        self.task_buttons = []
        self.setWindowTitle('Simulator Controller 安装引导'); self.resize(760, 650)
        layout = QVBoxLayout(self); layout.setSpacing(12)
        title = QLabel('Simulator Controller 安装引导'); title.setObjectName('section'); layout.addWidget(title)
        note = QLabel('启用邻车、旗号和策略播报。一键完成官方便携版下载、基础配置和中文语音接入；已有安装直接复用。'); note.setWordWrap(True); layout.addWidget(note)
        one_click = QPushButton('一键安装并接入（推荐）'); one_click.setObjectName('primary'); one_click.clicked.connect(self.install_and_connect); layout.addWidget(one_click)
        self.task_buttons.append(one_click)
        self.statuses = []
        for text, actions in [
            ('1 · 安装组件', [('下载并安装', self.install), ('选择已有安装目录', self.select_root)]),
            ('2 · 保存基础配置', [('打开 Simulator Setup', self.open_setup), ('查看官方说明', self.open_docs)]),
            ('3 · 接入中文播报', [('接入中文播报', self.configure), ('启动 Simulator Controller', self.open_startup)])]:
            title = QLabel(text); title.setObjectName('section'); layout.addWidget(title)
            status = QLabel(); status.setWordWrap(True); self.statuses.append(status); layout.addWidget(status)
            row = QHBoxLayout()
            for name, fn in actions:
                b = QPushButton(name); b.clicked.connect(fn); row.addWidget(b)
                if fn != self.open_docs: self.task_buttons.append(b)
                if fn == self.configure: self.configure_button = b
                if fn == self.open_setup: self.setup_button = b
                if fn == self.open_startup: self.startup_button = b
            layout.addLayout(row)
        note = QLabel('基础配置：选择 iRacing 和简体中文，启用赛事工程师、赛事观察员、赛事策略师，保存基础配置。\n接入前关闭 Simulator Controller 各模块。接入会备份原配置；完成后重新启动它，再到助手首页启动播报并进游戏测试。'); note.setWordWrap(True); layout.addWidget(note)
        self.progress = QProgressBar(); self.progress.setRange(0, 100); self.progress.setValue(0)
        self.progress.setFormat('%p%'); self.progress.setMinimumHeight(28)
        self.progress.setStyleSheet('QProgressBar{background:#e5effa;border:1px solid #bcd6ee;border-radius:8px;text-align:center;color:#244765;font-weight:bold;} QProgressBar::chunk{background:#60aafa;border-radius:7px;}')
        layout.addWidget(self.progress)
        self.progress_note = QLabel('等待开始安装'); self.progress_note.setWordWrap(True); layout.addWidget(self.progress_note)
        hint = QLabel('模拟进度仅用于显示任务运行状态；安装结果以完成提示为准。'); hint.setObjectName('muted'); hint.setWordWrap(True); layout.addWidget(hint)
        row = QHBoxLayout(); self.refresh_button = QPushButton('重新检测'); self.refresh_button.clicked.connect(self.refresh); row.addWidget(self.refresh_button)
        close = QPushButton('关闭'); close.clicked.connect(self.close); row.addWidget(close); layout.addLayout(row)
        self.refresh()

    def refresh(self):
        try:
            self.state = inspect_simulator(self.backend.project)
        except (OSError, ValueError, UnicodeError) as e:
            self.message('读取配置失败：' + str(e)); return
        s = self.state
        self.statuses[0].setText(('已安装：' if s['installed'] else '未找到安装：') + str(s['root']))
        self.statuses[1].setText(('已保存基础配置：' if s['configured'] else '尚未保存基础配置：') + str(s['ini']))
        self.statuses[2].setText('已接入中文播报；请启动组件并进游戏验证。' if s['integrated'] else '尚未接入，或配置与当前语音端口不一致。')
        busy = self.task_active
        for button in self.task_buttons: button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        self.configure_button.setEnabled(s['installed'] and s['configured'] and not busy)
        self.setup_button.setEnabled(s['installed'] and not busy); self.startup_button.setEnabled(s['installed'] and not busy)

    def message(self, text, visible=True):
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open('a', encoding='utf-8') as f:
                f.write(datetime.now().isoformat(timespec='seconds') + ' ' + text + '\n')
        except OSError: pass
        if visible: self.progress_note.setText(text)

    def begin_progress(self):
        self.task_active = True; self.pending_output = ''
        self.progress.setValue(1); self.progress_timer.start()
        self.refresh_button.setObjectName('')
        self.refresh_button.style().unpolish(self.refresh_button); self.refresh_button.style().polish(self.refresh_button)
        self.message('正在准备安装，请稍候……')
        self.refresh()

    def advance_progress(self):
        if self.task_active: self.progress.setValue(min(99, self.progress.value() + 1))

    def run(self, program, args):
        if self.job is not None and self.job.state() != QProcess.NotRunning:
            self.message('已有任务运行中，请等待完成。'); return
        self.begin_progress()
        self.job = QProcess(self); self.job.setProcessChannelMode(QProcess.MergedChannels)
        self.job.setWorkingDirectory(str(self.backend.root)); self.job.readyReadStandardOutput.connect(self.read_output)
        self.job.finished.connect(self.on_task_finished); self.job.errorOccurred.connect(self.failed)
        self.job.start(str(program), [str(x) for x in args])

    def read_output(self):
        if self.job is None: return
        text = bytes(self.job.readAllStandardOutput()).decode('utf-8', errors='replace')
        if text: self.message(text.rstrip(), visible=False)
        self.pending_output += text
        while '\n' in self.pending_output:
            line, self.pending_output = self.pending_output.split('\n', 1)
            if '正在下载' in line or '下载官方便携版' in line: self.progress_note.setText('正在下载组件，请稍候……')
            elif '准备 iRacing' in line: self.progress_note.setText('正在保存基础配置……')
            elif '备份原配置并接入' in line: self.progress_note.setText('正在接入中文语音……')
            elif '镜像' in line: self.progress_note.setText('正在切换下载源，请稍候……')

    def on_task_finished(self, code, status):
        self.read_output(); self.progress_timer.stop(); self.task_active = False
        success = code == 0 and status == QProcess.NormalExit
        if success:
            self.progress.setValue(100)
            self.message('安装和接入完成。请点击“重新检测”，然后重启播报助手。')
            self.refresh_button.setObjectName('primary')
        else:
            self.progress.setValue(min(99, self.progress.value()))
            self.message('任务未完成。请重新检测后重试。诊断日志：' + str(self.log_path))
        self.refresh_button.style().unpolish(self.refresh_button); self.refresh_button.style().polish(self.refresh_button)
        self.refresh()

    def failed(self, error):
        self.progress_timer.stop(); self.task_active = False
        self.message('任务未完成：' + self.job.errorString() + '。请重新检测后重试。'); self.refresh()

    def install(self):
        self.run('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-WindowStyle', 'Hidden', '-File', self.backend.project / 'scripts/install-simulator-controller.ps1'])
        self.message('正在下载官方安装器；请在弹出的安装器中完成安装。')

    def select_root(self):
        folder = QFileDialog.getExistingDirectory(self, '选择 Simulator Controller 目录', str(self.state['root']))
        if not folder: return
        from pathlib import Path
        if not (Path(folder) / 'Binaries/Simulator Startup.exe').is_file():
            QMessageBox.warning(self, '目录不正确', '请选择包含 Binaries/Simulator Startup.exe 的 Simulator Controller 目录。'); return
        path = self.backend.project / 'config/local.json'
        config = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
        config['simulator_controller'] = folder; atomic_json(path, config); self.refresh()

    def install_and_connect(self):
        self.run(self.backend.python, ['-u', '-X', 'utf8', self.backend.root / 'install_simulator.py'])

    def launch(self, filename):
        path = self.state['root'] / 'Binaries' / filename
        if not path.is_file(): self.message('未找到程序：' + str(path)); return
        ok, _ = QProcess.startDetached(str(path), [], str(path.parent))
        if not ok: self.message('无法启动：' + str(path))

    def open_setup(self): self.launch('Simulator Setup.exe')
    def open_startup(self): self.launch('Simulator Startup.exe')
    def open_docs(self): QDesktopServices.openUrl(QUrl(GUIDE_URL))

    def configure(self):
        import psutil
        root = self.state['root'].resolve()
        for process in psutil.process_iter(['exe']):
            try:
                from pathlib import Path
                if process.info['exe'] and Path(process.info['exe']).resolve().is_relative_to(root):
                    self.message('请先关闭 Simulator Controller 各模块，再点击接入。'); return
            except (psutil.Error, OSError): continue
        self.run(self.backend.python, ['-X', 'utf8', self.backend.root / 'setup_simulator.py'])

    def closeEvent(self, event):
        if self.job is not None and self.job.state() != QProcess.NotRunning:
            self.message('安装或接入任务尚未结束，请完成后关闭。'); event.ignore()
        else: event.accept()
