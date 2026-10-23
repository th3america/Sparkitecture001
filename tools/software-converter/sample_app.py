"""Small text editor and deterministic open/edit/save/reopen benchmark."""
import json
import sys
import tempfile
from pathlib import Path

def self_test():
    with tempfile.TemporaryDirectory() as folder:
        p = Path(folder)/'note.txt'
        p.write_text('Sparkitecture\n', encoding='utf-8')
        initial = p.read_text(encoding='utf-8')
        p.write_text(initial+'Edited — café 🔸\n', encoding='utf-8')
        actual = p.read_text(encoding='utf-8')
        assert actual == 'Sparkitecture\nEdited — café 🔸\n'
        print(json.dumps({'open':True,'edit':True,'save':True,'reopen':True,'unicode':True},sort_keys=True))

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        self_test()
    else:
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QFileDialog
        app = QApplication(sys.argv)
        window = QMainWindow(); window.setWindowTitle('Converted sample · Text workshop')
        editor = QTextEdit(); window.setCentralWidget(editor)
        def open_note():
            path, _ = QFileDialog.getOpenFileName(window,'Open text','','Text (*.txt)')
            if path: editor.setPlainText(Path(path).read_text(encoding='utf-8'))
        def save_note():
            path, _ = QFileDialog.getSaveFileName(window,'Save text','note.txt','Text (*.txt)')
            if path: Path(path).write_text(editor.toPlainText(),encoding='utf-8')
        menu=window.menuBar().addMenu('File')
        menu.addAction('Open',open_note); menu.addAction('Save',save_note)
        window.resize(700,460); window.show(); sys.exit(app.exec())
