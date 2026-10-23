
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
import html as html_module
from pathlib import Path

from PySide6.QtCore import QMimeData, QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QImage, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QMainWindow, QMessageBox,
    QTextEdit, QStatusBar
)

APP_NAME = "AI Notepad v1.1"
NATIVE_EXT = ".ainote"
SUPPORTED_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}


class NoteEditor(QTextEdit):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setAcceptRichText(True)
        self.setUndoRedoEnabled(True)

    def insertFromMimeData(self, source: QMimeData) -> None:
        if source.hasImage():
            image = source.imageData()
            if isinstance(image, QImage):
                self.owner.insert_qimage(image)
                return

        if source.hasUrls():
            inserted_any = False
            for url in source.urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.suffix.lower() in SUPPORTED_IMAGES and p.is_file():
                        self.owner.insert_image_file(p)
                        inserted_any = True
            if inserted_any:
                return

        # Keep text simple like Notepad: paste plain text instead of rich HTML.
        if source.hasText():
            self.insertPlainText(source.text())
            return

        super().insertFromMimeData(source)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.suffix.lower() in SUPPORTED_IMAGES:
                        event.acceptProposedAction()
                        return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            files = []
            for url in mime.urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.suffix.lower() in SUPPORTED_IMAGES and p.is_file():
                        files.append(p)
            if files:
                cursor = self.cursorForPosition(event.position().toPoint())
                self.setTextCursor(cursor)
                for p in files:
                    self.owner.insert_image_file(p)
                event.acceptProposedAction()
                return
        super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Untitled - {APP_NAME}")
        self.resize(1100, 760)

        self.editor = NoteEditor(self)
        self.setCentralWidget(self.editor)

        self.current_path: Path | None = None
        self.modified = False
        self._temporary_dirs = []
        self.image_dir = self._new_image_dir()
        self.image_paths: dict[str, Path] = {}

        self._build_menus()
        self._build_status()

        self.editor.textChanged.connect(self._on_changed)
        self.editor.cursorPositionChanged.connect(self.update_stats)

        self.stats_timer = QTimer(self)
        self.stats_timer.setSingleShot(True)
        self.stats_timer.timeout.connect(self.update_stats)

        self.update_stats()

    # ---------- UI ----------

    def _build_menus(self):
        menu_file = self.menuBar().addMenu("&File")
        menu_edit = self.menuBar().addMenu("&Edit")
        menu_format = self.menuBar().addMenu("F&ormat")
        menu_view = self.menuBar().addMenu("&View")
        menu_help = self.menuBar().addMenu("&Help")

        def add(menu, text, shortcut, func):
            action = QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(func)
            menu.addAction(action)
            return action

        add(menu_file, "&New", "Ctrl+N", self.new_note)
        add(menu_file, "&Open...", "Ctrl+O", self.open_note)
        add(menu_file, "&Save", "Ctrl+S", self.save_note)
        add(menu_file, "Save &As...", "Ctrl+Shift+S", self.save_as)
        menu_file.addSeparator()
        add(menu_file, "Insert &Image...", "Ctrl+I", self.insert_image_dialog)
        menu_file.addSeparator()
        add(menu_file, "Export &Text...", None, self.export_text)
        add(menu_file, "Export &HTML...", None, self.export_html)
        add(menu_file, "Export &ZIP...", None, self.export_zip)
        menu_file.addSeparator()
        add(menu_file, "E&xit", "Alt+F4", self.close)

        add(menu_edit, "&Undo", "Ctrl+Z", self.editor.undo)
        add(menu_edit, "&Redo", "Ctrl+Y", self.editor.redo)
        menu_edit.addSeparator()
        add(menu_edit, "Cu&t", "Ctrl+X", self.editor.cut)
        add(menu_edit, "&Copy", "Ctrl+C", self.editor.copy)
        add(menu_edit, "&Paste", "Ctrl+V", self.editor.paste)
        add(menu_edit, "&Delete", "Del", lambda: self.editor.textCursor().removeSelectedText())
        menu_edit.addSeparator()
        add(menu_edit, "Select &All", "Ctrl+A", self.editor.selectAll)
        add(menu_edit, "&Find...", "Ctrl+F", self.find_text)

        self.word_wrap_action = QAction("&Word Wrap", self, checkable=True)
        self.word_wrap_action.setChecked(True)
        self.word_wrap_action.toggled.connect(
            lambda checked: self.editor.setLineWrapMode(
                QTextEdit.WidgetWidth if checked else QTextEdit.NoWrap
            )
        )
        menu_format.addAction(self.word_wrap_action)

        self.status_action = QAction("&Status Bar", self, checkable=True)
        self.status_action.setChecked(True)
        self.status_action.toggled.connect(self.statusBar().setVisible)
        menu_view.addAction(self.status_action)

        add(menu_help, "&About", None, self.about)

    def _build_status(self):
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ln 1, Col 1 | Words 0 | Chars 0 | Lines 1 | Images 0 | UTF-8")

    # ---------- Counts ----------

    def _on_changed(self):
        self.modified = True
        self._update_title()
        self.stats_timer.start(120)

    def update_stats(self):
        text = self.editor.toPlainText()
        words = len(re.findall(r"\S+", text))
        chars = len(text)
        lines = text.count("\n") + 1

        cursor = self.editor.textCursor()
        block = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1

        html = self.editor.document().toHtml()
        images = html.lower().count("<img")

        self.statusBar().showMessage(
            f"Ln {block}, Col {col} | Words {words:,} | Chars {chars:,} | "
            f"Lines {lines:,} | Images {images} | UTF-8"
        )

    # ---------- Images ----------

    def insert_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Insert Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.insert_image_file(Path(path))

    def insert_image_file(self, path: Path):
        image = QImage(str(path))
        if image.isNull():
            QMessageBox.warning(self, APP_NAME, f"Could not open image:\n{path}")
            return
        self.insert_qimage(image, source_suffix=path.suffix.lower())

    def insert_qimage(self, image: QImage, source_suffix: str = ".png"):
        if image.isNull():
            return

        # Keep oversized screenshots manageable in the editor.
        max_width = max(400, self.editor.viewport().width() - 60)
        if image.width() > max_width:
            image = image.scaledToWidth(max_width, Qt.SmoothTransformation)

        ext = source_suffix if source_suffix in SUPPORTED_IMAGES else ".png"
        name = f"img_{uuid.uuid4().hex}{ext}"
        out = self.image_dir / name

        fmt = "PNG"
        if ext in {".jpg", ".jpeg"}:
            fmt = "JPG"
        elif ext == ".webp":
            fmt = "WEBP"

        if not image.save(str(out), fmt):
            # Fallback to PNG if the requested codec is unavailable.
            name = f"img_{uuid.uuid4().hex}.png"
            out = self.image_dir / name
            image.save(str(out), "PNG")

        self.image_paths[name] = out

        self.editor.document().setBaseUrl(QUrl.fromLocalFile(str(self.image_dir) + os.sep))
        cursor = self.editor.textCursor()
        cursor.insertImage(name)
        cursor.insertText("\n")
        self.editor.setTextCursor(cursor)

    # ---------- Native note format ----------

    def _new_image_dir(self):
        temp = tempfile.TemporaryDirectory(prefix="ai_notepad_images_")
        self._temporary_dirs.append(temp)
        return Path(temp.name)

    @staticmethod
    def _image_names(document):
        names = set()
        block = document.begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid() and fragment.charFormat().isImageFormat():
                    names.add(fragment.charFormat().toImageFormat().name())
                it += 1
            block = block.next()
        return names

    def _active_images(self):
        # Retain removed image resources for Undo, but export only visible ones.
        return {name: self.image_paths[name]
                for name in self._image_names(self.editor.document())
                if name in self.image_paths}

    @staticmethod
    def _rewrite_image_sources(html, mapping):
        def replace(match):
            old = html_module.unescape(match.group(2))
            return match.group(1) + html_module.escape(mapping.get(old, old), quote=True) + match.group(3)
        return re.sub(r'(<img\b[^>]*\bsrc=")([^"]*)(")', replace, html, flags=re.I)

    def _load_html_from(self, path):
        html = path.read_text(encoding="utf-8")
        document = QTextDocument()
        document.setHtml(html)
        image_dir = self._new_image_dir()
        images, mapping = {}, {}
        try:
            for source in self._image_names(document):
                url = QUrl(source)
                if url.isLocalFile():
                    original = Path(url.toLocalFile())
                elif url.isRelative():
                    original = path.parent / url.path()
                else:
                    raise ValueError("Only local HTML images can be imported.")
                if not original.is_file():
                    raise ValueError(f"Missing HTML image: {source}")
                name = f"img_{uuid.uuid4().hex}{original.suffix.lower()}"
                shutil.copy2(original, image_dir / name)
                images[name] = image_dir / name
                mapping[source] = name
            html = self._rewrite_image_sources(document.toHtml(), mapping)
        except Exception:
            self._temporary_dirs.pop().cleanup()
            raise
        self.image_dir, self.image_paths = image_dir, images
        self.editor.document().setBaseUrl(QUrl.fromLocalFile(str(image_dir) + os.sep))
        self.editor.setHtml(html)

    def _manifest(self):
        text = self.editor.toPlainText()
        return {
            "format": "ai-notepad-note-v1",
            "encoding": "utf-8",
            "words": len(re.findall(r"\S+", text)),
            "characters": len(text),
            "lines": text.count("\n") + 1,
            "images": sorted(self._active_images()),
        }

    def _save_native_to(self, path: Path):
        html = self.editor.document().toHtml()
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("document.html", html.encode("utf-8"))
            z.writestr("manifest.json", json.dumps(self._manifest(), indent=2).encode("utf-8"))
            for name, img_path in self._active_images().items():
                if img_path.exists():
                    z.write(img_path, f"images/{name}")

    def _load_native_from(self, path: Path):
        # Validate required content before changing the current document state.
        with zipfile.ZipFile(path, "r") as z:
            html = z.read("document.html").decode("utf-8")
            document = QTextDocument()
            document.setHtml(html)
            names = self._image_names(document)
            payload = {}
            for name in names:
                if Path(name).name != name or '/' in name or '\\' in name:
                    raise ValueError(f"Invalid native image name: {name}")
                payload[name] = z.read(f"images/{name}")
        images_dir = self._new_image_dir()
        try:
            for name, data in payload.items():
                (images_dir / name).write_bytes(data)
        except Exception:
            self._temporary_dirs.pop().cleanup()
            raise
        self.image_dir = images_dir
        self.image_paths = {name: images_dir / name for name in payload}
        self.editor.document().setBaseUrl(QUrl.fromLocalFile(str(images_dir) + os.sep))
        self.editor.setHtml(html)

    # ---------- File actions ----------

    def maybe_save(self) -> bool:
        if not self.modified:
            return True
        reply = QMessageBox.question(
            self,
            APP_NAME,
            "Save changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        )
        if reply == QMessageBox.Save:
            return self.save_note()
        if reply == QMessageBox.Cancel:
            return False
        return True

    def new_note(self):
        if not self.maybe_save():
            return
        self.editor.clear()
        self.current_path = None
        self.image_dir = self._new_image_dir()
        self.image_paths = {}
        self.modified = False
        self._update_title()

    def open_note(self):
        if not self.maybe_save():
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open",
            "",
            "AI Notepad (*.ainote);;Text Files (*.txt);;HTML Files (*.html *.htm);;All Files (*.*)"
        )
        if not path:
            return

        self.open_path(Path(path))

    def open_path(self, path: Path):
        """Load a path selected by the dialog or supplied at process launch."""
        p = Path(path)
        try:
            if p.suffix.lower() == NATIVE_EXT:
                self._load_native_from(p)
            elif p.suffix.lower() in {".html", ".htm"}:
                self._load_html_from(p)
            else:
                self.editor.setPlainText(p.read_text(encoding="utf-8", errors="replace"))
                self.image_paths = {}

            self.current_path = p
            self.modified = False
            self._update_title()
            self.update_stats()
            return True
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Open failed:\n{exc}")
            return False

    def save_note(self) -> bool:
        if self.current_path is None or self.current_path.suffix.lower() != NATIVE_EXT:
            return self.save_as()
        try:
            self._save_native_to(self.current_path)
            self.modified = False
            self._update_title()
            return True
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Save failed:\n{exc}")
            return False

    def save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save As",
            "Untitled.ainote",
            "AI Notepad (*.ainote)"
        )
        if not path:
            return False

        p = Path(path)
        if p.suffix.lower() != NATIVE_EXT:
            p = p.with_suffix(NATIVE_EXT)

        try:
            self._save_native_to(p)
            self.current_path = p
            self.modified = False
            self._update_title()
            return True
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Save failed:\n{exc}")
            return False

    def export_text(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Text", "note.txt", "Text Files (*.txt)")
        if path:
            Path(path).write_text(self.editor.toPlainText(), encoding="utf-8")

    def export_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export HTML", "note.html", "HTML Files (*.html)")
        if not path:
            return
        p = Path(path)
        asset_dir = p.with_name(p.stem + "_images")
        asset_dir.mkdir(parents=True, exist_ok=True)

        html = self.editor.document().toHtml()
        for name, img_path in self._active_images().items():
            if img_path.exists():
                dest = asset_dir / name
                shutil.copy2(img_path, dest)
                html = html.replace(f'src="{name}"', f'src="{asset_dir.name}/{name}"')
        p.write_text(html, encoding="utf-8")

    def export_zip(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export ZIP", "note.zip", "ZIP Files (*.zip)")
        if not path:
            return
        p = Path(path)
        if p.suffix.lower() != ".zip":
            p = p.with_suffix(".zip")

        html = self._rewrite_image_sources(
            self.editor.document().toHtml(),
            {name: f"images/{name}" for name in self._active_images()}
        )
        with zipfile.ZipFile(p, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("document.html", html.encode("utf-8"))
            z.writestr("document.txt", self.editor.toPlainText().encode("utf-8"))
            z.writestr("stats.json", json.dumps(self._manifest(), indent=2).encode("utf-8"))
            for name, img_path in self._active_images().items():
                if img_path.exists():
                    z.write(img_path, f"images/{name}")

    # ---------- Find / About ----------

    def find_text(self):
        from PySide6.QtWidgets import QInputDialog
        term, ok = QInputDialog.getText(self, "Find", "Find:")
        if ok and term:
            if not self.editor.find(term):
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.Start)
                self.editor.setTextCursor(cursor)
                if not self.editor.find(term):
                    QMessageBox.information(self, APP_NAME, f'"{term}" not found.')

    def about(self):
        QMessageBox.information(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME}\n\n"
            "A simple Notepad-style editor with live counts and inline image support.\n"
            "Native .ainote files preserve text and images in one portable file."
        )

    def _update_title(self):
        name = self.current_path.name if self.current_path else "Untitled"
        star = "*" if self.modified else ""
        self.setWindowTitle(f"{star}{name} - {APP_NAME}")

    def closeEvent(self, event):
        if self.maybe_save():
            for temp in self._temporary_dirs:
                temp.cleanup()
            self._temporary_dirs.clear()
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # Fusion is stable across Win10 installs while retaining native-looking controls.
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_path(Path(sys.argv[1]))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
