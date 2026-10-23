# AI Notepad v1.1

The existing Sparkitecture desktop app for text, images, word/character/line counts, and portable `.ainote` documents.

[Download AI Notepad](AI-Notepad-v1.1-Windows.zip?raw=true)

## Run on Windows

1. Install Python 3.11+ with the Windows `py` launcher. This app was tested with Python 3.12.
2. Download and extract the ZIP into a writable folder.
3. Double-click `run.bat`. First launch creates a local environment and installs PySide6 from the internet.
4. Choose File > Open to open your `.ainote`. After first setup, `launch.vbs` starts the app without a console.

This is the existing Python desktop app and launch scripts, not a standalone EXE. The included `build_windows.bat` can build an EXE with PyInstaller.

## Files and exports

An `.ainote` is a ZIP container holding document HTML, a measurement manifest, and embedded images. Open it directly in AI Notepad. File > Export Text saves text without images; Export HTML saves HTML with an accompanying image folder; Export ZIP bundles HTML, text, statistics, and images.

[Return to Sparkitecture Basics](../../sparkitecture-basics/README.md).

App source and launch scripts are unchanged from the local v1.1 app. Personal notes, caches, and the machine-specific virtual environment are excluded. Dependencies install through requirements.txt.
