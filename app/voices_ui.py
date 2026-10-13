"""Protected two-role voice library and asynchronous import interface."""
import json,sys,uuid  # Collected for the dynamically loaded backend voice library.
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QTimer,QProcess
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QDialog,QLineEdit,QFormLayout,QFileDialog,QPlainTextEdit,QMessageBox)

class ImportDialog(QDialog):
    def __init__(self,backend,parent=None):
        super().__init__(parent);self.backend=backend;self.setWindowTitle('添加 GPT-SoVITS 音色');self.resize(850,630)
        from voice_library import repository
        self.repository=repository;self.pool=ThreadPoolExecutor(max_workers=1);self.future=None;self.source=None;self.job=None
        layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        self.name=QLineEdit();form.addRow('音色名称',self.name)
        self.url=QLineEdit();self.url.setPlaceholderText('https://huggingface.co/用户名/仓库/tree/main/目录')
        row=QHBoxLayout();row.addWidget(self.url);self.fetch=QPushButton('读取仓库');self.fetch.clicked.connect(self.fetch_repository);row.addWidget(self.fetch);form.addRow('Hugging Face',row)
        self.files={}
        for field,title,pattern in [('gpt','GPT 权重','*.ckpt'),('sovits','SoVITS 权重','*.pth'),('reference','参考录音','*.wav *.mp3 *.flac *.ogg')]:
            combo=QComboBox();combo.setEditable(True);self.files[field]=combo;row=QHBoxLayout();row.addWidget(combo,1)
            browse=QPushButton('本地文件');browse.clicked.connect(lambda checked=False,f=field,p=pattern:self.browse(f,p));row.addWidget(browse);form.addRow(title,row)
        self.text=QLineEdit();self.text.setPlaceholderText('逐字填写参考录音中的中文台词');form.addRow('参考台词',self.text)
        self.notes=QLabel('需要配套 .ckpt 与 .pth，以及 3~10 秒参考录音。支持 v1、v2、v2Pro、v2ProPlus 中文音色。');self.notes.setWordWrap(True);layout.addWidget(self.notes)
        self.log=QPlainTextEdit();self.log.setReadOnly(True);layout.addWidget(self.log,1)
        row=QHBoxLayout();self.submit=QPushButton('导入音色');self.submit.clicked.connect(self.import_voice);row.addWidget(self.submit);self.close_button=QPushButton('关闭');self.close_button.clicked.connect(self.reject);row.addWidget(self.close_button);layout.addLayout(row)
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(200)
    def browse(self,field,pattern):
        name,_=QFileDialog.getOpenFileName(self,'选择文件','','音色文件 ('+pattern+')')
        if name:
            if self.source:
                for combo in self.files.values():combo.clear()
            self.source=None
            self.files[field].setEditText(name)
            self.notes.setText('本地导入模式；请选择三个本地文件。')
    def fetch_repository(self):
        if self.future:return
        self.fetch.setEnabled(False);self.submit.setEnabled(False);self.log.appendPlainText('读取仓库文件清单…')
        self.future=self.pool.submit(self.repository,self.url.text())
    def tick(self):
        if not self.future or not self.future.done():return
        try:
            self.source=self.future.result()
            for field,combo in self.files.items():
                combo.clear();suffixes={'gpt':('.ckpt',),'sovits':('.pth',),'reference':('.wav','.mp3','.flac','.ogg')}[field]
                combo.addItems([x['path'] for x in self.source['files'] if Path(x['path']).suffix.lower() in suffixes])
            self.notes.setText('仓库：'+self.source['repo']+'；许可：'+str(self.source['license'])+'。请选择配套模型和参考录音。')
            self.log.appendPlainText('文件清单已读取，下载固定于版本 '+self.source['revision'][:12])
        except Exception as e:self.log.appendPlainText('读取失败：'+str(e))
        self.future=None;self.fetch.setEnabled(True);self.submit.setEnabled(True)
    def import_voice(self):
        if self.job:return
        if not self.name.text().strip() or not self.text.text().strip() or any(not c.currentText().strip() for c in self.files.values()):
            self.log.appendPlainText('请填写音色名称、参考台词并选择三个文件。');return
        request={'name':self.name.text().strip(),'reference_text':self.text.text().strip(),'files':{k:c.currentText() for k,c in self.files.items()},'source':self.source}
        path=self.backend.root/'voice_import_request.json';path.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8')
        self.job=QProcess(self);self.job.setProgram(str(self.backend.python));self.job.setArguments(['-X','utf8',str(self.backend.root/'voice_library.py'),'import','--request',str(path)])
        self.job.setWorkingDirectory(str(self.backend.root));self.job.setProcessChannelMode(QProcess.MergedChannels)
        self.job.readyReadStandardOutput.connect(lambda:self.log.appendPlainText(bytes(self.job.readAllStandardOutput()).decode('utf-8',errors='replace').strip()))
        self.job.finished.connect(self.import_finished);self.job.errorOccurred.connect(self.process_error)
        self.submit.setEnabled(False);self.fetch.setEnabled(False);self.close_button.setEnabled(False);self.job.start()
    def import_finished(self,code,status):
        self.job=None;self.submit.setEnabled(True);self.fetch.setEnabled(True);self.close_button.setEnabled(True)
        (self.backend.root/'voice_import_request.json').unlink(missing_ok=True)
        if code==0:self.accept()
        else:self.log.appendPlainText('导入失败，已保留原音色配置。')
    def process_error(self,error):
        self.log.appendPlainText('导入进程无法启动或异常退出。')
        if error==QProcess.FailedToStart:self.import_finished(1,QProcess.NormalExit)
    def reject(self):
        if self.job:return
        self.timer.stop();self.pool.shutdown(wait=False,cancel_futures=True);super().reject()
    def accept(self):
        self.timer.stop();self.pool.shutdown(wait=False,cancel_futures=True);super().accept()

class VoiceLibraryWidget(QWidget):
    def __init__(self,backend,changed,parent=None):
        super().__init__(parent);self.backend=backend;self.changed=changed
        sys.path.insert(0,str(backend.root))
        from voice_library import Catalog
        self.catalog=Catalog(backend.root);v=QVBoxLayout(self);v.addWidget(QLabel('默认音色：克洛琳德、芙宁娜（不可删除）'))
        self.roles={};form=QFormLayout()
        for role,title in [('engineer','工程师'),('observer','观察员／策略师')]:self.roles[role]=QComboBox();form.addRow(title,self.roles[role])
        v.addLayout(form);apply=QPushButton('保存角色音色');apply.clicked.connect(self.apply);v.addWidget(apply)
        self.list=QComboBox();v.addWidget(self.list);row=QHBoxLayout();add=QPushButton('添加音色');add.clicked.connect(self.add);row.addWidget(add);self.delete=QPushButton('删除自定义音色');self.delete.clicked.connect(self.remove);row.addWidget(self.delete);v.addLayout(row)
        self.list.currentIndexChanged.connect(self.selection);self.result=QLabel('导入后选择角色音色，保存后重启播报生效。');self.result.setWordWrap(True);v.addWidget(self.result);self.refresh()
    def refresh(self):
        entries=self.catalog.entries();roles=self.catalog.roles()
        for role,combo in self.roles.items():
            combo.clear()
            for key,item in entries.items():combo.addItem(item['name']+(' · 默认' if item['builtin'] else ''),key)
            combo.setCurrentIndex(combo.findData(roles[role]))
        self.list.clear()
        for key,item in entries.items():self.list.addItem(item['name']+(' · 默认' if item['builtin'] else ''),key)
        self.selection()
    def selection(self):self.delete.setEnabled(bool(self.list.currentData()) and self.list.currentData() not in ('clorinde','furina'))
    def apply(self):
        self.catalog.assign_roles({role:c.currentData() for role,c in self.roles.items()});self.result.setText('角色音色已保存。正在更新播报服务。');self.changed()
    def add(self):
        dialog=ImportDialog(self.backend,self)
        if dialog.exec()==QDialog.Accepted:self.refresh();self.result.setText('音色已添加，请选择要使用它的角色。')
    def remove(self):
        key=self.list.currentData()
        if key in ('clorinde','furina'):return
        if QMessageBox.question(self,'删除自定义音色','删除所选自定义音色？正在使用它的角色将恢复默认音色。')!=QMessageBox.Yes:return
        self.catalog.delete(key);self.refresh();self.changed();self.result.setText('自定义音色已删除，默认音色保留。')
