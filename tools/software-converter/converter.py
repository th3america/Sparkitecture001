from __future__ import annotations
import json
import os
import shutil
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QFontDatabase, QFont
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QLineEdit,QComboBox,QCheckBox,QPlainTextEdit,QFileDialog,QMessageBox,QListWidget,QStackedWidget,
    QGridLayout,QFrame,QScrollArea,QProgressBar)
from engine import Engine, Store, inspect_source, METHODS

STYLE='''
QWidget { background:#111821; color:#e5ecf4; font-family:Segoe UI; font-size:13px; }
QMainWindow { background:#111821; }
QFrame#card { background:#1a2430; border:1px solid #334353; border-radius:12px; }
QFrame#card QLabel, QFrame#card QCheckBox { background:transparent; }
QLabel#title { font-size:27px; font-weight:700; color:#fff3dc; }
QLabel#eyebrow { color:#f6b65c; font-size:12px; font-weight:700; }
QLabel#muted { color:#a1b2c4; }
QPushButton { background:#263546; border:1px solid #40556c; border-radius:7px; padding:9px 16px; }
QPushButton:hover { background:#334a60; }
QPushButton:disabled { color:#657688; background:#1c2630; }
QPushButton#primary { background:#efad55; color:#171c24; font-weight:700; border:none; }
QLineEdit,QComboBox,QPlainTextEdit { background:#0e151d; border:1px solid #3b4b5e; border-radius:6px; padding:7px; selection-background-color:#316363; }
QListWidget { background:#0d141c; border:none; padding:8px; }
QListWidget::item { padding:15px 10px; border-radius:7px; }
QListWidget::item:selected { background:#263b45; color:#8de0cb; }
QCheckBox { spacing:9px; padding:4px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #71859a; border-radius:3px; background:#101820; }
QCheckBox::indicator:checked { background:#65c4ad; border:2px solid #a5e6d7; }
QProgressBar { border:none; background:#23303c; height:5px; }
QProgressBar::chunk { background:#69c8b5; }
QScrollArea { border:none; }
'''

class Worker(QThread):
    message=Signal(str); done=Signal(dict)
    def __init__(self, store, args):
        super().__init__(); self.engine=Engine(store,self.message.emit); self.args=args
    def run(self):
        try: self.done.emit(self.engine.convert(**self.args))
        except Exception as e: self.done.emit({'status':'FAILED','error':str(e)})

class Window(QMainWindow):
    def __init__(self, root=None):
        super().__init__()
        self.setWindowTitle('Sparkitecture · Software Converter'); self.resize(1240,880); self.setAcceptDrops(True)
        if os.name == 'nt':
            for name in ('segoeui.ttf','segoeuib.ttf','seguisym.ttf','seguiemj.ttf'):
                QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name))
        self.setFont(QFont('Segoe UI',10))
        self.store=Store(root or Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'Sparkitecture'/'SoftwareConverter')
        self.worker=None; self.last=None
        self.settings_path=self.store.root/'settings.json'
        try: settings=json.loads(self.settings_path.read_text())
        except (OSError,ValueError): settings={}
        outer=QWidget(); self.setCentralWidget(outer); layout=QHBoxLayout(outer); layout.setContentsMargins(0,0,0,0)
        self.nav=QListWidget(); self.nav.setFixedWidth(210)
        self.nav.addItems(['Converter','Workshop','Local Intelligence','AI Handoff','Jobs & Receipts','Settings'])
        layout.addWidget(self.nav); self.pages=QStackedWidget(); layout.addWidget(self.pages,1)
        page=QWidget(); v=QVBoxLayout(page); v.setContentsMargins(26,24,26,24); v.setSpacing(14)
        self.label(v,'SPARKITECTURE  /  LOCAL WORKSHOP','eyebrow')
        self.label(v,'Software Converter','title')
        self.label(v,'Standalone first · Adaptive methods · Optional AI handoff','muted')
        card, c=self.card(); v.addWidget(card)
        self.label(c,'New conversion  •  Drop an application or source project')
        row=QHBoxLayout(); self.source=QLineEdit(); self.source.setPlaceholderText('Drop a file / folder here, or browse…'); row.addWidget(self.source,1)
        self.button(row,'File',self.pick_file); self.button(row,'Folder',self.pick_folder); self.button(row,'Sample',self.sample)
        c.addLayout(row)
        row=QHBoxLayout(); self.button(row,'Inspect source',self.inspect); self.detected=QLabel('Automatic source detection · awaiting input'); self.detected.setWordWrap(True); row.addWidget(self.detected,1); c.addLayout(row)
        row=QHBoxLayout(); row.addWidget(QLabel('Entrypoint')); self.entry=QComboBox(); self.entry.setMinimumWidth(250); row.addWidget(self.entry,1); c.addLayout(row)
        self.label(v,'Convert to  •  choose one or more destinations','eyebrow')
        targets=QGridLayout(); self.targets=[]
        for i,(name,formats) in enumerate([('Windows',['EXE','MSI','MSIX']),('Linux',['AppImage','DEB','RPM','Executable']),('macOS',['APP','DMG','PKG']),('Android',['Installed App','APK','AAB'])]):
            frame,box=self.card(); self.label(box,name)
            for fmt in formats:
                check=QCheckBox(fmt); check.setChecked(name=='Windows' and fmt=='EXE'); box.addWidget(check); self.targets.append((name,fmt,check))
            targets.addWidget(frame,0,i)
        v.addLayout(targets)
        selection=QHBoxLayout()
        self.button(selection,'Select all',lambda:[c.setChecked(True) for _,_,c in self.targets])
        self.button(selection,'Clear',lambda:[c.setChecked(False) for _,_,c in self.targets]); selection.addStretch(); v.addLayout(selection)
        self.label(v,'Installed App means an installed Android launcher app; APK and AAB are separate targets.','muted')
        frame,box=self.card(); v.addWidget(frame)
        row=QHBoxLayout(); row.addWidget(QLabel('Conversion intelligence')); self.method=QComboBox(); self.method.addItems(METHODS); row.addWidget(self.method,1); box.addLayout(row)
        self.label(box,'Available now: Python source → native one-file executable via configured PyInstaller. Other routes produce diagnostic handoffs.','muted')
        self.run_test=QCheckBox('Allow running source and output for the selected behavioral test'); box.addWidget(self.run_test)
        self.test_args=QLineEdit(); self.test_args.setPlaceholderText('Test arguments as JSON, e.g. ["--self-test"]. Empty = build only.'); box.addWidget(self.test_args)
        self.label(box,'Build tools run locally. Test execution has your user permissions; isolation is not a security sandbox. AI is never called automatically.','muted')
        row=QHBoxLayout(); self.start=self.button(row,'Convert && verify',self.convert,True); self.stop=self.button(row,'Stop',self.cancel); self.stop.setEnabled(False)
        self.button(row,'Open results',self.open_results); row.addStretch(); v.addLayout(row)
        self.progress=QProgressBar(); self.progress.setRange(0,1); self.progress.setValue(0); self.progress.setTextVisible(False); v.addWidget(self.progress)
        self.status=QLabel('READY · Real local jobs. No simulated success states.'); v.addWidget(self.status)
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMinimumHeight(110); v.addWidget(self.log)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(page); self.pages.addWidget(scroll)
        self.workshop=self.text_page('Workshop','METHOD LIBRARY\n\nDirect / PyInstaller: implemented for Python source and the host OS. Requires an explicit entrypoint and configured toolchain.\n\nHybrid, behavioral rebuild, compatibility, macOS packages, Android packages, and native installers: planned adapters. Selecting one creates an unresolved job and diagnostic handoff.\n\nSmart Auto selects an applicable local route. A validated recipe is recognized only for matching source, entrypoint, target, toolchain and test arguments. Failed attempts are retained. No claim of arbitrary binary conversion.\n\nPause/resume and automated AI patch import are future capabilities. Stop cancels the active process tree. Completed artifacts and receipts are retained.')
        self.intelligence=self.text_page('Local Intelligence','')
        self.handoffs=self.text_page('AI Handoff','')
        self.history=self.text_page('Jobs & Receipts','')
        s=QWidget(); sv=QVBoxLayout(s); sv.setContentsMargins(30,30,30,30); self.label(sv,'Settings','title')
        self.label(sv,'Build Python interpreter','eyebrow')
        self.python=QLineEdit(settings.get('python',shutil.which('python') or '')); sv.addWidget(self.python)
        self.button(sv,'Browse interpreter',self.pick_python)
        self.label(sv,'Select Python with PyInstaller and your project dependencies installed. The converter does not download or install dependencies.','muted')
        self.button(sv,'Save settings',self.save_settings)
        self.label(sv,'Local storage: '+str(self.store.root),'muted')
        self.label(sv,'Optional AI: manual export only. Handoffs contain receipts and logs, which may include local paths. Review them before sharing. Source is excluded by default.','muted'); sv.addStretch(); self.pages.addWidget(s)
        self.nav.currentRowChanged.connect(self.show_page); self.nav.setCurrentRow(0)
        self.setStyleSheet(STYLE)

    def label(self, layout, text, name=''):
        x=QLabel(text); x.setWordWrap(True); x.setObjectName(name); layout.addWidget(x); return x
    def card(self):
        x=QFrame(); x.setObjectName('card'); box=QVBoxLayout(x); box.setContentsMargins(16,14,16,14); return x,box
    def button(self,layout,text,fn,primary=False):
        b=QPushButton(text); b.clicked.connect(fn)
        if primary: b.setObjectName('primary')
        layout.addWidget(b); return b
    def text_page(self,title,body):
        p=QWidget(); box=QVBoxLayout(p); box.setContentsMargins(30,30,30,30); self.label(box,title,'title')
        text=QPlainTextEdit(body); text.setReadOnly(True); box.addWidget(text)
        self.button(box,'Refresh',self.refresh); self.button(box,'Open local records',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.root/'jobs'))))
        self.pages.addWidget(p); return text
    def show_page(self,index): self.pages.setCurrentIndex(index); self.refresh()
    def refresh(self):
        self.intelligence.setPlainText(json.dumps(self.store.recipes(),indent=2) or 'No recipes yet.')
        jobs=self.store.jobs(); self.history.setPlainText(json.dumps(jobs,indent=2))
        self.handoffs.setPlainText('Manual AI handoff · no automatic upload\n\n'+ '\n\n'.join(f"{j['id']} · {j['status']}\n{j['handoff']}" for j in jobs if j.get('handoff')))
    def pick_file(self):
        p,_=QFileDialog.getOpenFileName(self,'Choose application or source','','All files (*)')
        if p: self.source.setText(p); self.inspect()
    def pick_folder(self):
        p=QFileDialog.getExistingDirectory(self,'Choose source project')
        if p: self.source.setText(p); self.inspect()
    def pick_python(self):
        p,_=QFileDialog.getOpenFileName(self,'Choose build Python','','Executables (*)')
        if p: self.python.setText(p)
    def save_settings(self):
        self.settings_path.write_text(json.dumps({'python':self.python.text().strip()},indent=2)); self.status.setText('Settings saved locally.')
    def sample(self):
        root=Path(getattr(sys,'_MEIPASS',Path(__file__).parent)); destination=self.store.root/'samples'/'text-editor'; destination.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/'sample_app.py',destination/'main.py'); self.source.setText(str(destination)); self.test_args.setText('["--self-test"]'); self.inspect()
        self.log.appendPlainText('Sample loaded. Enable test execution to compare actual open/edit/save/reopen behavior.')
    def inspect(self):
        try:
            info=inspect_source(self.source.text()); self.entry.clear(); self.entry.addItem('Automatic (single entrypoint only)','')
            for entry in info['entrypoints']: self.entry.addItem(entry,entry)
            self.detected.setText(f"{info['format']} · {info['source_os']} · {info['architecture']}")
            self.log.setPlainText(json.dumps(info,indent=2)); self.status.setText('INSPECTED · Input read; no source code executed.')
        except Exception as e: QMessageBox.warning(self,'Inspection',str(e))
    def convert(self):
        try:
            targets=[(n,f) for n,f,c in self.targets if c.isChecked()]
            if not targets: raise ValueError('Select a destination.')
            if not Path(self.source.text()).exists(): raise ValueError('Choose a real input first.')
            args=json.loads(self.test_args.text()) if self.test_args.text().strip() else None
            if args is not None and (not isinstance(args,list) or not all(isinstance(x,str) for x in args)): raise ValueError('Test arguments must be a JSON array of strings.')
            if args is not None and not self.run_test.isChecked(): self.log.appendPlainText('Execution not authorized: building without behavior tests.')
            self.save_settings(); self.start.setEnabled(False); self.stop.setEnabled(True); self.progress.setRange(0,0)
            self.worker=Worker(self.store,dict(source=self.source.text(),targets=targets,method=self.method.currentText(),python=self.python.text().strip(),entry=self.entry.currentData() or '',test_args=args,allow_execution=self.run_test.isChecked()))
            self.worker.message.connect(self.log.appendPlainText); self.worker.done.connect(self.finished); self.worker.start(); self.status.setText('RUNNING · Logs and receipts retained locally')
        except Exception as e: QMessageBox.warning(self,'Conversion',str(e))
    def cancel(self):
        if self.worker: self.worker.engine.stop.set(); self.status.setText('STOP REQUESTED · Waiting for process cleanup')
    def finished(self,data):
        self.last=data; self.start.setEnabled(True); self.stop.setEnabled(False); self.progress.setRange(0,1); self.progress.setValue(1)
        self.status.setText(data['status']+' · '+data.get('id','')); self.log.appendPlainText(json.dumps(data,indent=2)); self.refresh()
    def open_results(self):
        p=self.store.root/'jobs'
        if self.last and self.last.get('id'): p=p/self.last['id']
        p.mkdir(parents=True,exist_ok=True); QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
    def dropEvent(self,event):
        urls=event.mimeData().urls()
        if urls and urls[0].isLocalFile(): self.source.setText(urls[0].toLocalFile()); self.inspect()
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.cancel(); event.ignore(); self.status.setText('Stopping active job. Close again after it finishes.')
        else: event.accept()

def main():
    app=QApplication(sys.argv); app.setStyle('Fusion'); window=Window(); window.show(); sys.exit(app.exec())

if __name__=='__main__': main()
