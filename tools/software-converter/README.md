# Sparkitecture Software Converter — local prototype 0.1

> [!WARNING]
> **SOFTWARE CONVERTER: HAS NOT BEEN LIVE TESTED. HAVE YOUR AI TEST IT BEFORE USE.**
> Development checks and sample conversions have been run; real-world use on your applications and system has not been validated.

A real desktop conversion workshop with a full six-section interface: Converter, Workshop, Local Intelligence, AI Handoff, Jobs & Receipts, and Settings.

## Downloads

[Windows desktop EXE](https://github.com/th3america/Sparkitecture001/releases/download/software-converter-v0.1/Sparkitecture-Software-Converter.exe) | [AI / automation CLI EXE](https://github.com/th3america/Sparkitecture001/releases/download/software-converter-v0.1/Sparkitecture-Converter-CLI.exe) | [Complete package](https://github.com/th3america/Sparkitecture001/releases/download/software-converter-v0.1/Sparkitecture-Software-Converter-v0.1-Windows.zip)

The unsigned Windows x64 executables run without a separate Python install. Conversion builds require a configured external Python/PyInstaller toolchain. In the downloaded ZIP the EXEs are at the top level.

## Run

Open `dist/Sparkitecture-Software-Converter.exe` on Windows x64. The UI and inspection work without Python or AI. To build Python projects, select an external Python interpreter with PyInstaller and the project's dependencies in Settings. No API key, paid model, or automatic dependency download is required.

For source development, install `requirements.txt`, then run `python converter.py`.

## AI / automation access

Use `dist/Sparkitecture-Converter-CLI.exe` for JSON-based inspection, conversion, job queries, recipes and diagnostic handoffs. It shares the desktop engine and records. Start with `capabilities`; see [AI tool guide](AI-TOOL-GUIDE.md) for commands, permission controls, schemas and exit codes. AI is an optional caller, not a required runtime.

## First conversion

1. Select **Sample**, or drop a Python project folder / ZIP / script.
2. Inspect automatic source detection and choose an entrypoint if there are several.
3. Select Windows → EXE. The original OS remains a selectable destination.
4. Set the build Python interpreter in Settings.
5. For the sample, enable test execution and retain `["--self-test"]` in test arguments.
6. Choose **Convert & verify**. Open results to inspect the executable, logs, and `receipt.json`.

The sample compares actual text file creation, reading, editing, saving, reopening, and Unicode output between the source and packaged executable. This is selected-test coverage, not proof of every GUI behavior.

## What works

- File/folder import and drag/drop; Python source, ZIP, PE, ELF and Mach-O inspection, with explicit unknowns.
- Local Python → native single-file executable adapter using the configured PyInstaller toolchain.
- Sequential per-destination jobs, process-tree cancellation, retained logs, SQLite history, SHA-256 receipts.
- Optional source/output execution with explicit arguments, bounded timeouts, and baseline comparison.
- Exact-condition recipe recognition; success and failure records remain separate. Reused recipes are retested.
- Diagnostic ZIP handoffs for unresolved work; no automatic AI calls or external uploads. Source is excluded; review logs before sharing.

## Available interface, future adapters

The full destination and method interface is retained. MSI/MSIX, Linux packaging, macOS, Android installation/packages, hybrid reconstruction, behavioral rebuilding, compatibility runtimes, remote workers, pause/resume, and automatic AI solution import are not implemented. They produce unresolved diagnostics rather than simulated output. Smart Auto currently selects the one applicable local adapter; it does not invent new conversion algorithms.

## Operational limits

Build/test processes run under the current user's permissions, not a security sandbox. Source/output execution is opt-in; imported code should be trusted. Builds can invoke project hooks. Import is limited to 256 MiB and 10,000 files, and common environment/build directories are excluded. ZIP traversal, symlinks and duplicate destination names are rejected. Same-project working files may be included; review inputs and receipts. Project data/resources may require a future custom PyInstaller recipe.

Local state defaults to `%LOCALAPPDATA%/Sparkitecture/SoftwareConverter`. The converter does not modify input files. It stages a copy for builds. It does not promise that the source architecture or OS can always be inferred.

## Build and test

`python -m unittest test_engine -v`

`python -m PyInstaller --clean --noconfirm --onefile --windowed --name Sparkitecture-Software-Converter --add-data "sample_app.py;." converter.py`

`python -m PyInstaller --noconfirm --onefile --console --name Sparkitecture-Converter-CLI cli.py`

Windows dependency versions are pinned to the Qt runtime verified during AI Notepad packaging. Other platforms need native build and testing. Published under tools/software-converter in Sparkitecture001.
