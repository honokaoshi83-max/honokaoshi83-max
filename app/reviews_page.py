"""Latest saved review dashboard; historical files remain untouched."""
import json,math,statistics,subprocess
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QEvent
from PySide6.QtGui import QColor,QTextBlockFormat,QTextCursor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QScrollArea,QFrame,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QTextBrowser,QSizePolicy,QLayout)
from review_store import recent_reviews,duration,lap_duration

TABLE_STYLE='''
QTableWidget{background:#f9fcff;border:1px solid #d4e4f2;border-radius:10px;gridline-color:#dce9f4;}
QTableWidget::item{padding:3px 10px;border:0;font-size:12px;}
QHeaderView::section{background:#e7f2ff;color:#315c83;padding:5px;border:0;border-bottom:1px solid #c8def1;font-weight:600;font-size:12px;}
'''

class CommentView(QTextBrowser):
    def text(self):return self.toPlainText()
    def setText(self,text):
        self.setPlainText(text.replace('\n\n','\n'))
        cursor=QTextCursor(self.document());cursor.select(QTextCursor.Document)
        block=QTextBlockFormat();block.setBottomMargin(5);block.setLineHeight(120,QTextBlockFormat.ProportionalHeight.value)
        cursor.mergeBlockFormat(block)
        self.moveCursor(QTextCursor.Start);self.verticalScrollBar().setValue(0)

def shown(value):return '—' if value is None or value=='' else str(value)
def elapsed(value):return duration(value) if isinstance(value,(int,float)) and math.isfinite(value) and value>=0 else '—'
def lap(value):return lap_duration(value) if isinstance(value,(int,float)) and math.isfinite(value) and value>0 else '—'
def local_time(value):return shown(value).replace('T',' ')

def lap_stats(row):
    """Stored TT statistics or display-only pace derived from race samples."""
    if isinstance(row.get('stats'),dict) and row['stats']:return row['stats']
    rows=[r for r in row.get('laps',[]) if isinstance(r,dict)]
    if not rows:return {}
    timed=[r['seconds'] for r in rows if isinstance(r.get('seconds'),(int,float)) and math.isfinite(r['seconds']) and 10<=r['seconds']<=3600]
    valid=[r['seconds'] for r in rows if r.get('valid') and isinstance(r.get('seconds'),(int,float)) and math.isfinite(r['seconds']) and 10<=r['seconds']<=3600]
    return dict(observed_laps=len(rows),valid_laps=len(valid),invalid_laps=sum(not r.get('valid') for r in rows),
                best_valid=min(valid) if valid else None,valid_average=statistics.mean(valid) if valid else None,
                standard_deviation=statistics.pstdev(timed) if timed else None)

class ReviewsPage(QScrollArea):
    def __init__(self,project):
        super().__init__();self.project=Path(project).resolve();self.entries=[];self.signature=None;self._fit_scheduled=False
        self.setWidgetResizable(True);self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body=QWidget();self.setWidget(body);v=QVBoxLayout(body);self.body_layout=v;v.setSizeConstraint(QLayout.SetNoConstraint);v.setContentsMargins(18,12,18,12);v.setSpacing(9)
        row=QHBoxLayout();title=QLabel('复盘');title.setObjectName('title');row.addWidget(title);row.addStretch()
        refresh=QPushButton('刷新');refresh.clicked.connect(lambda:self.refresh(force=True));row.addWidget(refresh)
        folder=QPushButton('打开复盘文件夹');folder.clicked.connect(self.open_folder);row.addWidget(folder);v.addLayout(row)
        note=QLabel('展示最近一次已保存的比赛复盘。历史文本保留在文件夹中。');note.setObjectName('muted');note.setWordWrap(True);v.addWidget(note)
        panel=QFrame();self.data_panel=panel;panel.setObjectName('card');panel.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Ignored);box=QVBoxLayout(panel);box.setContentsMargins(16,10,16,10);box.setSpacing(5)
        heading=QHBoxLayout();self.latest_title=QLabel('最近一次比赛');self.latest_title.setObjectName('section');self.latest_title.setWordWrap(True);heading.addWidget(self.latest_title,1)
        self.open_latest=QPushButton('查看复盘文本');self.open_latest.clicked.connect(self.reveal_latest);heading.addWidget(self.open_latest);box.addLayout(heading)
        self.record_time=QLabel('等待比赛复盘');self.record_time.hide()
        self.details=QTableWidget(0,6);self.details.setObjectName('reviewDetails');self.details.setStyleSheet(TABLE_STYLE)
        self.details.setHorizontalHeaderLabels(['项目','数据']*3);self.details.verticalHeader().hide()
        self.details.setEditTriggers(QAbstractItemView.NoEditTriggers);self.details.setSelectionMode(QAbstractItemView.NoSelection);self.details.setFocusPolicy(Qt.NoFocus)
        self.details.setWordWrap(False);self.details.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Ignored);self.details.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.details.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.details.verticalHeader().setMinimumSectionSize(16);self.details.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.details.horizontalHeader().setFixedHeight(24)
        for column in range(6):self.details.horizontalHeader().setSectionResizeMode(column,QHeaderView.Stretch)
        box.addWidget(self.details,1)
        self.data_note=QLabel();self.data_note.setObjectName('muted');self.data_note.setStyleSheet('font-size:11px;');self.data_note.setWordWrap(True);box.addWidget(self.data_note);v.addWidget(panel,5)
        evaluation_panel=QFrame();self.evaluation_panel=evaluation_panel;evaluation_panel.setObjectName('card');evaluation_panel.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Ignored);ev=QVBoxLayout(evaluation_panel);ev.setContentsMargins(18,12,18,12);ev.setSpacing(7)
        label=QLabel('复盘评价');self.evaluation_title=label;label.setObjectName('section');label.setMaximumHeight(32);ev.addWidget(label)
        self.evaluation=CommentView();self.evaluation.setOpenExternalLinks(False);self.evaluation.setFrameShape(QFrame.NoFrame);self.evaluation.setStyleSheet('QTextBrowser{font-size:14px;color:#2b5275;background:transparent;border:0;padding:0;}');ev.addWidget(self.evaluation,1);v.addWidget(evaluation_panel,1)
        self.evaluation.textChanged.connect(self.schedule_fit);self.evaluation.viewport().installEventFilter(self)
        self.notice=QLabel();self.notice.setWordWrap(True);self.notice.setObjectName('muted');self.notice.hide();v.addWidget(self.notice)
        self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(3000);self.refresh(force=True)

    def show_review(self,row):
        self.open_latest.setEnabled(bool(row));mode='Time Trial' if row and row.get('mode')=='time_trial' else '正赛'
        self.latest_title.setText(f"{shown(row.get('track'))} · {mode}" if row else '最近一次比赛')
        self.record_time.setText(('最后记录时间：' if row.get('left_early') else '比赛结束时间：')+local_time(row.get('ended_at',row.get('saved_at'))) if row else '等待比赛复盘')
        row=row or {};stats=lap_stats(row)
        pairs=[('赛道',shown(row.get('track'))),('模式',mode if row else '—'),('赛道布局',shown(row.get('layout'))),('车辆',shown(row.get('car'))),
               ('记录开始',local_time(row.get('started_at'))),('记录结束',local_time(row.get('ended_at'))),
               ('比赛总用时',elapsed(row.get('total_seconds'))),('已记录用时',elapsed(row.get('observed_seconds'))),
               ('完成圈数',shown(row.get('completed'))),('采集完成圈数',shown(stats.get('observed_laps')))]
        if row.get('mode')=='race':
            pos=row.get('position');cars=row.get('cars');grid=row.get('grid')
            pairs.extend([('总排名',f'{pos} / {cars}' if pos and cars else shown(pos)),('组别排名',shown(row.get('class_position'))),
                          ('发车名次',shown(grid)),('名次变化',f'{grid-pos:+d}' if grid and pos else '—')])
        observed=stats.get('observed_laps');invalid=stats.get('invalid_laps');sd=stats.get('standard_deviation')
        pairs.extend([('最快有效圈',lap(stats.get('best_valid'))),('有效平均圈速',lap(stats.get('valid_average'))),
                      ('有效圈数',shown(stats.get('valid_laps'))),('犯规无效圈数',shown(invalid)),
                      ('圈速标准差',f'{sd:.3f}秒' if isinstance(sd,(int,float)) and math.isfinite(sd) else '—'),
                      ('无效圈比例',f'{invalid/observed:.1%}' if observed and isinstance(invalid,(int,float)) else '—'),
                      ('稳定性评价',{'good':'稳定','medium':'有波动','poor':'需改善'}.get(stats.get('stability'),'—')),
                      ('结束原因',shown(row.get('reason')))])
        self.details.clearContents();self.details.setRowCount((len(pairs)+2)//3)
        for index,(key,value) in enumerate(pairs):
            r=index//3;c=(index%3)*2
            for col,text in ((c,key),(c+1,value)):
                item=QTableWidgetItem(text);item.setToolTip(text)
                if col%2==0:item.setBackground(QColor('#edf5fd'));item.setForeground(QColor('#507797'))
                self.details.setItem(r,col,item)
        for r in range(self.details.rowCount()):
            for c in range(self.details.columnCount()):
                if self.details.item(r,c) is None:self.details.setItem(r,c,QTableWidgetItem(''))
        notes=[]
        if row and row.get('total_seconds') is None:notes.append('未完整记录比赛起止，总用时暂缺。')
        if row.get('expected_end_at'):notes.append('预计赛事结束：'+local_time(row['expected_end_at'])+'（按退出前剩余时间估算）')
        if row.get('mode')=='race':notes.append('排名来源：'+row.get('position_source','SDK最后观测值，最终结果未确认'))
        if stats:notes.append('圈速统计基于已采集完成圈；犯规无效圈计入稳定性。')
        self.data_note.setText('  '.join(notes));self.data_note.setToolTip('\n'.join(notes));self.data_note.setVisible(bool(notes))
        self.evaluation.setText('\n\n'.join(str(x) for x in row.get('summary',[]) if x) or '暂无复盘评价。完成符合条件的正赛或 Time Trial 后会自动生成。')
        self.fit_table()

    def fit_table(self):
        self._fit_scheduled=False
        self.details.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        total=self.data_panel.height()+self.evaluation_panel.height()
        if total<=0:return
        share=1/6
        if self.entries:
            # Measure formatted paragraphs at their available width, rather than
            # counting characters; this also adapts when the window is resized.
            doc=self.evaluation.document().clone()
            doc.setTextWidth(max(1,self.evaluation.viewport().width()))
            content=doc.documentLayout().documentSize().height();doc.deleteLater()
            layout=self.evaluation_panel.layout();margins=layout.contentsMargins()
            chrome=margins.top()+margins.bottom()+self.evaluation_title.sizeHint().height()+layout.spacing()+4
            share=min(.4,max(1/6,(content+chrome)/total))
        lower=round(share*6000);upper=6000-lower
        for widget,weight in ((self.data_panel,upper),(self.evaluation_panel,lower)):
            if self.body_layout.stretch(self.body_layout.indexOf(widget))!=weight:self.body_layout.setStretchFactor(widget,weight)

    def schedule_fit(self):
        if not self._fit_scheduled:
            self._fit_scheduled=True;QTimer.singleShot(0,self.fit_table)

    def eventFilter(self,watched,event):
        if hasattr(self,'evaluation') and watched is self.evaluation.viewport() and event.type()==QEvent.Resize:self.schedule_fit()
        return super().eventFilter(watched,event)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'evaluation'):self.schedule_fit()

    def refresh(self,force=False):
        folder=self.project/'复盘'
        try:
            signature=folder.stat().st_mtime_ns if folder.exists() else 0
            status=self.project/'work/race-voices/review_status.json';error=None
            if status.exists():error=json.loads(status.read_text(encoding='utf-8-sig')).get('error')
            if force or signature!=self.signature:
                self.signature=signature;self.entries=recent_reviews(self.project,limit=1);self.show_review(self.entries[0] if self.entries else None)
            self.notice.setText(error or '')
            self.notice.setVisible(bool(error))
        except (OSError,ValueError) as error:self.show_notice('读取复盘失败：'+str(error))

    def show_notice(self,text):
        self.notice.setText(text);self.notice.setVisible(bool(text))

    def reveal_latest(self):
        if self.entries:self.reveal(self.entries[0]['path'])

    def reveal(self,path):
        target=Path(path).resolve();folder=(self.project/'复盘').resolve()
        if folder.parent!=self.project or target.parent!=folder or target.suffix.lower()!='.txt' or not target.is_file():
            self.show_notice('对应文本不存在，请刷新页面。');return
        try:subprocess.Popen(['explorer.exe','/select,',str(target)])
        except OSError as error:self.show_notice('打开文件位置失败：'+str(error))

    def open_folder(self):
        folder=self.project/'复盘'
        try:
            if folder.resolve().parent!=self.project:raise OSError('复盘目录链接无效')
            folder.mkdir(exist_ok=True);subprocess.Popen(['explorer.exe',str(folder)])
        except OSError as error:self.show_notice('打开复盘文件夹失败：'+str(error))
