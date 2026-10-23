# Give AI Notepad to your AI for another OS

Download and extract the [source ZIP](AI-Notepad-v1.1-Windows.zip?raw=true). Give the folder to an AI with coding and file access and tell it your OS and processor. Copy this request:

> Adapt this existing AI Notepad app for my operating system and processor. Read ai_notepad.py, requirements.txt, and test_ai_notepad.py. Preserve editing, Unicode, images, counts, undo/redo, Find, .ainote open/save, and TXT/HTML/ZIP exports. Build on my target OS or a matching runner. Replace Windows launch scripts with appropriate native packaging. Keep .ainote files compatible. Run the tests, launch the packaged app, and verify opening, saving, reopening notes with images, and exports. Deliver a ready-to-run download, launch instructions, checksum, and a record of what you actually tested. Report missing capabilities honestly. Exclude private notes and local environments.

## Build guidance for your AI

- Start with the existing Python/PySide6 source. Preserve behavior while adapting platform details.
- Use an isolated environment on the target OS and CPU. Run `python -m unittest test_ai_notepad -v`. Headless tests can use `QT_QPA_PLATFORM=offscreen`; separately test the packaged GUI.
- macOS: build a native `.app` on macOS and deliver a ZIP or DMG. Check Intel versus Apple silicon and report signing/notarization status.
- Linux: build on a suitable distribution baseline. Verify Qt plugins, display dependencies, executable permissions, and glibc compatibility. Deliver and test an appropriate executable or app bundle.
- A Windows EXE cannot become a macOS or Linux app by renaming it. Build from source on a native machine, VM, or matching CI runner.
- Check Unicode, line endings, image paths, dialogs, and temporary-file cleanup. Retain originals and report changes.

No macOS or Linux binary has been built or tested for this Windows release.

References: [PyInstaller operating model](https://pyinstaller.org/en/stable/operating-mode.html) and [build options](https://pyinstaller.org/en/stable/usage.html).
