import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QFileDialog
from PySide6.QtGui import QImage
from PySide6.QtCore import QMimeData
from ai_notepad import MainWindow

APP = QApplication.instance() or QApplication([])

class NoteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.w = MainWindow()

    def tearDown(self):
        self.w.modified = False
        self.w.close()
        self.w.deleteLater()
        APP.processEvents()
        self.temp.cleanup()

    def image(self):
        im = QImage(160, 80, QImage.Format_RGB32)
        im.fill(0x287F8F)
        self.w.insert_qimage(im)

    def test_native_roundtrip_text_and_image(self):
        self.w.editor.setPlainText('Ember ⟡🔸\nUnicode café\n')
        self.image()
        expected = self.w.editor.toPlainText()
        p = self.root/'roundtrip.ainote'
        self.w._save_native_to(p)
        self.w.editor.clear()
        self.w._load_native_from(p)
        self.assertEqual(self.w.editor.toPlainText(), expected)
        self.assertEqual(len(self.w.image_paths), 1)

    def test_open_path_restores_text_images_and_title(self):
        self.w.editor.setPlainText('Launch-path reload ⟡🔸')
        self.image()
        expected = self.w.editor.toPlainText()
        p = self.root/'launch.ainote'
        self.w._save_native_to(p)
        self.w.editor.clear()
        self.assertTrue(self.w.open_path(p))
        self.assertEqual(self.w.editor.toPlainText(), expected)
        self.assertEqual(len(self.w.image_paths), 1)
        self.assertFalse(self.w.modified)
        self.assertIn('launch.ainote', self.w.windowTitle())

    def test_zip_html_image_links_resolve(self):
        self.image()
        p = self.root/'export.zip'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(p), '')):
            self.w.export_zip()
        with zipfile.ZipFile(p) as z:
            refs = re.findall(r'<img[^>]+src="([^"]+)"', z.read('document.html').decode())
            self.assertTrue(refs)
            self.assertTrue(all(ref in z.namelist() for ref in refs), refs)

    def test_removed_images_not_saved(self):
        self.image()
        self.w.editor.selectAll()
        self.w.editor.textCursor().removeSelectedText()
        p = self.root/'empty.ainote'
        self.w._save_native_to(p)
        with zipfile.ZipFile(p) as z:
            self.assertEqual(json.loads(z.read('manifest.json'))['images'], [])
            self.assertFalse(any(n.startswith('images/') for n in z.namelist()))

    def test_html_import_preserves_images_in_native_save(self):
        self.image()
        p = self.root/'export.html'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(p), '')):
            self.w.export_html()
        self.w.modified = False
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(p), '')):
            self.w.open_note()
        p2 = self.root/'import.ainote'
        self.w._save_native_to(p2)
        with zipfile.ZipFile(p2) as z:
            self.assertEqual(len(json.loads(z.read('manifest.json'))['images']), 1)

    def test_failed_native_open_preserves_current_image_state(self):
        self.image()
        old_dir, old_images = self.w.image_dir, self.w.image_paths.copy()
        bad = self.root/'bad.ainote'
        with zipfile.ZipFile(bad, 'w') as z:
            z.writestr('manifest.json', '{}')
        with self.assertRaises(Exception):
            self.w._load_native_from(bad)
        self.assertEqual(self.w.image_dir, old_dir)
        self.assertEqual(self.w.image_paths, old_images)

    def test_plain_paste_and_undo(self):
        mime = QMimeData()
        mime.setHtml('<b>rich</b>')
        mime.setText('plain ⟡🔸')
        self.w.editor.insertFromMimeData(mime)
        self.assertEqual(self.w.editor.toPlainText(), 'plain ⟡🔸')
        self.w.editor.undo()
        self.assertEqual(self.w.editor.toPlainText(), '')

    def test_export_text_and_counts(self):
        text = 'one two\n⟡🔸 café\n'
        self.w.editor.setPlainText(text)
        self.w.update_stats()
        self.assertEqual(self.w._manifest()['characters'], len(text))
        self.assertEqual(self.w._manifest()['lines'], 3)
        p = self.root/'note.txt'
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(str(p), '')):
            self.w.export_text()
        self.assertEqual(p.read_text(encoding='utf-8'), text)

if __name__ == '__main__':
    unittest.main(verbosity=2)
