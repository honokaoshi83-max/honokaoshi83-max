"""Experimental race strategy page: saved conditions and offline fuel preview."""
import json,math
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QFormLayout,
    QFrame,QLabel,QPushButton,QLineEdit,QComboBox,QDoubleSpinBox,QTableWidget,
    QTableWidgetItem,QHeaderView,QAbstractItemView,QScrollArea,QCheckBox)
from race_strategy import calculate_plan,save_plan,load_plan

def text(value,style=None):
    widget=QLabel(value);widget.setWordWrap(True)
    if style:widget.setObjectName(style)
    return widget

def card(title):
    widget=QFrame();widget.setObjectName('card');layout=QVBoxLayout(widget)
    layout.setContentsMargins(18,16,18,16);layout.setSpacing(10);layout.addWidget(text(title,'section'))
    return widget,layout

class StrategyPage(QScrollArea):
    def __init__(self,project):
        super().__init__();self.project=Path(project);self.path=self.project/'config/race-strategy.json'
        self.result=None;self.loading=True;self.fields={};self.sections=[]
        self.setWidgetResizable(True);self.setFrameShape(QFrame.NoFrame)
        body=QWidget();self.setWidget(body);v=QVBoxLayout(body);v.setContentsMargins(22,16,22,18);v.setSpacing(12)
        heading=QHBoxLayout();heading.addWidget(text('赛事策略','title'))
        badge=text('测试中');badge.setStyleSheet('color:#9a6111;background:#fff0c9;border:1px solid #edce84;border-radius:7px;padding:5px 12px;font-weight:600;');heading.addWidget(badge);heading.addStretch()
        self.enabled=QCheckBox('策略模块：关闭');self.enabled.setToolTip('手动开启策略模块；每次启动默认关闭。');self.enabled.setStyleSheet('QCheckBox{font-weight:600;color:#2375c5;spacing:8px;} QCheckBox::indicator{width:18px;height:18px;border:2px solid #7aabd4;border-radius:5px;background:white;} QCheckBox::indicator:checked{background:#2f83e8;border-color:#2f83e8;}');heading.addWidget(self.enabled)
        example=QPushButton('四小时示例');self.example_button=example;example.clicked.connect(self.example);heading.addWidget(example)
        new=QPushButton('新建计划');new.clicked.connect(self.reset);heading.addWidget(new);v.addLayout(heading)
        v.addWidget(text('赛前规划燃油与进站，先预览，再保存。','muted'))
        columns=QHBoxLayout();columns.setSpacing(12)
        box,left=card('赛事与燃油条件');box.setProperty('tone','blue');form=QFormLayout();form.setSpacing(8)
        self.name=QLineEdit();self.name.setPlaceholderText('例如：纽博格林四小时耐力赛');form.addRow('赛事名称',self.name)
        self.track=self.catalog('tracks');form.addRow('赛道及布局',self.track)
        self.car=self.catalog('cars');form.addRow('参赛车辆',self.car)
        self.mode=QComboBox();self.mode.addItem('限时','time');self.mode.addItem('限圈','laps')
        self.duration=self.spin('duration_minutes',1,1440,240,0,' 分钟');self.laps=self.spin('race_laps',1,20000,30,0,' 圈')
        row=QHBoxLayout();row.addWidget(self.mode);row.addWidget(self.duration,1);row.addWidget(self.laps,1);form.addRow('比赛长度',row)
        row=QHBoxLayout();row.addWidget(self.spin('initial_fuel',0,500,0,1,' 升'),1);row.addWidget(text('/ 上限'));row.addWidget(self.spin('capacity',0,500,0,1,' 升'),1);form.addRow('初始燃油',row)
        row=QHBoxLayout();row.addWidget(self.spin('lap_minutes',0,59,0,0,' 分'),1);row.addWidget(self.spin('lap_seconds',0,59.9,0,1,' 秒'),1);form.addRow('预计圈速',row)
        form.addRow('单圈油耗',self.spin('burn',0,100,0,2,' 升 / 圈'))
        form.addRow('安全储备',self.spin('reserve_laps',0,10,1,1,' 圈'));left.addLayout(form)
        row=QHBoxLayout();save=QPushButton('保存计划');save.clicked.connect(self.save);row.addWidget(save)
        generate=QPushButton('生成燃油预案');generate.setObjectName('primary');generate.setStyleSheet('QPushButton#primary:disabled{background:#e1ebf5;color:#8ea7bd;border:1px solid #ccdeec;}');generate.clicked.connect(self.generate);row.addWidget(generate);left.addLayout(row)
        columns.addWidget(box,1);self.sections.append(box)
        box,right=card('燃油预案');box.setProperty('tone','lavender');grid=QGridLayout();grid.setSpacing(12)
        self.metrics={}
        for i,(key,title) in enumerate([('stops','预计进站'),('laps','预计比赛圈数'),('first','首停窗口'),('add','首停建议补油')]):
            metric=QFrame();metric.setObjectName('card');m=QVBoxLayout(metric);m.setContentsMargins(12,9,12,9)
            m.addWidget(text(title,'muted'));value=text('—');value.setStyleSheet('font-size:24px;font-weight:650;color:#327bc4;');m.addWidget(value);self.metrics[key]=value;grid.addWidget(metric,i//2,i%2)
        right.addLayout(grid)
        self.basis=text('填写预计圈速和油耗后生成预案。','muted');right.addWidget(self.basis)
        self.notice=text('初始油量请在游戏内自行设置。');self.notice.setStyleSheet('color:#2373bc;');right.addWidget(self.notice)
        right.addStretch();note=text('当前提供离线预案；实时策略提醒、事故后重算与自动补油尚未启用。','muted');right.addWidget(note)
        columns.addWidget(box,1);self.sections.append(box);v.addLayout(columns)
        box,layout=card('进站计划');self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(['停次','预计进站','比赛用时约','建议补油','预计出站油量'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setMinimumHeight(120);self.table.setMaximumHeight(160)
        self.table.setStyleSheet('QTableWidget{background:rgba(255,255,255,180);border:0;gridline-color:#dfebf6;} QHeaderView::section{background:#e2efff;color:#315b81;border:0;padding:7px;} QTableWidget::item{padding:5px;}')
        layout.addWidget(self.table);self.table_hint=text('尚未生成计划。','muted');layout.addWidget(self.table_hint);v.addWidget(box);self.sections.append(box)
        box,layout=card('游戏连接');self.connection=text('等待游戏会话；实时策略执行尚未启用。','muted');layout.addWidget(self.connection);v.addWidget(box);v.addStretch()
        self.name.textChanged.connect(self.invalidate);self.track.currentTextChanged.connect(self.invalidate);self.car.currentTextChanged.connect(self.invalidate)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.enabled.toggled.connect(self.toggle_enabled)
        for widget in self.fields.values():widget.valueChanged.connect(self.invalidate)
        self.mode_changed();self.loading=False
        load_error=None
        try:
            saved=load_plan(self.path)
            if saved:self.set_conditions(saved);self.notice.setText('已恢复上次保存的条件。生成预案后查看。')
        except (OSError,ValueError) as error:load_error=str(error)
        self.toggle_enabled(False)
        if load_error:self.notice.setText(load_error)

    def toggle_enabled(self,enabled):
        self.invalidate()
        self.enabled.setText('策略模块：开启' if enabled else '策略模块：关闭')
        for section in self.sections:section.setEnabled(enabled)
        self.example_button.setEnabled(enabled)
        self.notice.setText('已开启，可填写并生成燃油预案。' if enabled else '策略模块已关闭，不计算、不跟踪、不播报。')
        if not enabled:self.table_hint.setText('开启策略模块后，填写条件并生成预案。')
        self.connection.setText('等待游戏会话；实时策略执行尚未启用。' if enabled else '策略模块已关闭。每次启动需手动开启；原有播报不受影响。')

    def catalog(self,key):
        combo=QComboBox();combo.setEditable(True);combo.setInsertPolicy(QComboBox.NoInsert);combo.setMinimumWidth(150);combo.addItem('')
        combo.lineEdit().setPlaceholderText('搜索选择，也可手动输入')
        try:
            rows=json.loads((self.project/'data'/f'{key}_zh.json').read_text(encoding='utf-8'))[key]
            combo.addItems(sorted({r['zh'] for r in rows}))
        except (OSError,ValueError,KeyError,TypeError):pass
        combo.completer().setFilterMode(Qt.MatchContains);combo.completer().setCaseSensitivity(Qt.CaseInsensitive)
        return combo

    def spin(self,key,minimum,maximum,value,decimals,suffix):
        widget=QDoubleSpinBox();widget.setRange(minimum,maximum);widget.setDecimals(decimals);widget.setSuffix(suffix);widget.setValue(value)
        widget.setStyleSheet('QDoubleSpinBox{background:white;border:1px solid #bad3eb;border-radius:6px;padding:6px;}')
        self.fields[key]=widget;return widget

    def mode_changed(self,*args):
        timed=self.mode.currentData()=='time';self.duration.setVisible(timed);self.laps.setVisible(not timed);self.invalidate()

    def conditions(self):
        return dict(name=self.name.text().strip(),track=self.track.currentText().strip(),car=self.car.currentText().strip(),mode=self.mode.currentData(),
            duration_minutes=self.duration.value(),race_laps=int(self.laps.value()),initial_fuel=self.fields['initial_fuel'].value(),
            capacity=self.fields['capacity'].value(),lap_seconds=self.fields['lap_minutes'].value()*60+self.fields['lap_seconds'].value(),
            burn=self.fields['burn'].value(),reserve_laps=self.fields['reserve_laps'].value())

    def invalidate(self,*args):
        if self.loading:return
        self.result=None;self.table.setRowCount(0)
        for widget in self.metrics.values():widget.setText('—')
        self.table_hint.setText('条件已改变，请重新生成预案。');self.basis.setText('计算依据：手动输入，尚未用实测油耗校准。');self.notice.setText('修改后请保存计划；生成结果不会自动保存。')

    def set_conditions(self,plan):
        self.loading=True
        try:
            self.name.setText(str(plan.get('name','')));self.track.setCurrentText(str(plan.get('track','')));self.car.setCurrentText(str(plan.get('car','')))
            index=self.mode.findData(plan.get('mode','time'));self.mode.setCurrentIndex(max(0,index))
            seconds=plan.get('lap_seconds',0)
            if not isinstance(seconds,(int,float)) or not math.isfinite(seconds):raise ValueError('保存的圈速无效。')
            values=dict(plan,lap_minutes=int(seconds//60),lap_seconds=seconds%60)
            for key,widget in self.fields.items():
                value=values.get(key,1 if key=='reserve_laps' else 0)
                if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not widget.minimum()<=value<=widget.maximum():raise ValueError('保存的策略条件无效。')
                widget.setValue(value)
        finally:self.loading=False
        self.mode_changed();self.invalidate()

    def reset(self):
        self.set_conditions(dict(mode='time',duration_minutes=240,race_laps=30,reserve_laps=1))
        self.notice.setText('新建草稿。点击保存后才会替换原计划。')

    def example(self):
        if not self.enabled.isChecked():return
        self.set_conditions(dict(name='纽博格林四小时耐力赛（示例）',track='纽博格林，实际参赛布局待选择',car='本田思域 Type R TCR',
            mode='time',duration_minutes=240,race_laps=30,initial_fuel=50,capacity=60,lap_seconds=480,burn=4,reserve_laps=1))
        self.generate();self.notice.setText('示例数据，仅演示计算；油耗、圈速和油量上限请按实车修改。')

    def generate(self):
        if not self.enabled.isChecked():return
        plan=self.conditions()
        self.invalidate()
        try:
            if not plan['track'] or not plan['car']:raise ValueError('请先选择赛道布局和参赛车辆。')
            result=calculate_plan(plan)
        except ValueError as error:self.notice.setText(str(error));return
        self.result=result;self.metrics['stops'].setText(str(result['stops'])+' 次');self.metrics['laps'].setText(str(result['race_laps'])+' 圈')
        first=result['first_stop'];self.metrics['first'].setText(('第 '+str(max(1,first-1))+'–'+str(first)+' 圈') if first else '无需加油')
        self.metrics['add'].setText(f"{result['schedule'][0]['add']:g} 升" if first else '0 升')
        self.table.setRowCount(len(result['schedule']))
        for i,row in enumerate(result['schedule']):
            minutes=round(row['minutes']);values=[str(row['number']),f"第 {row['lap']} 圈末",f'{minutes//60} 小时 {minutes%60:02d} 分',f"{row['add']:g} 升",f"{row['after']:g} 升"]
            for j,value in enumerate(values):self.table.setItem(i,j,QTableWidgetItem(value))
        self.basis.setText(f"手动预估：每圈 {plan['burn']:g} 升 · 安全储备 {result['reserve']:g} 升。"+('限时赛额外预留一圈完赛边界。' if plan['mode']=='time' else ''))
        self.table_hint.setText('进站圈为预估最晚圈；提前进站需重算补油量。未计入进站及维修耗时。')
        self.notice.setText('预案已生成，尚未启用游戏内策略执行。')

    def save(self):
        try:save_plan(self.path,self.conditions())
        except (OSError,ValueError) as error:self.notice.setText('保存失败：'+str(error));return
        self.notice.setText('计划已保存到本机。')

    def update_connection(self,state):
        if not self.enabled.isChecked():return
        if not state.get('game'):self.connection.setText('等待游戏会话；实时策略执行尚未启用。');return
        fuel=state.get('fuel');amount=f'{fuel:.1f} 升' if isinstance(fuel,(int,float)) and math.isfinite(fuel) else '暂无油量'
        self.connection.setText(f"已连接：{state.get('track','未知赛道')} · {state.get('car','未知车辆')} · {amount}。实时策略执行尚未启用。")
