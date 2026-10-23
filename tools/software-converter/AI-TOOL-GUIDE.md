# AI tool interface

The standalone smart converter is the worker. AI is an optional client that can inspect, run, diagnose, and consume its real evidence. No model integration or API subscription is required.

Use `Sparkitecture-Converter-CLI.exe` on Windows, or `python cli.py` from source. The desktop GUI and CLI share the engine and local SQLite store. Do not run multiple writers against the same input/output job intentionally.

## Discover before acting

```powershell
Sparkitecture-Converter-CLI.exe capabilities
Sparkitecture-Converter-CLI.exe inspect "C:\project"
Sparkitecture-Converter-CLI.exe --json-file inspection.json inspect "C:\project"
```

Read `implemented` and `unimplemented`; the future UI does not imply all routes are implemented.

## Build and verify

```powershell
Sparkitecture-Converter-CLI.exe convert "C:\project" --target Windows:EXE --entry main.py --python "C:\tools\python.exe"
Sparkitecture-Converter-CLI.exe convert "C:\project" --target Windows:EXE --entry main.py --python "C:\tools\python.exe" --allow-execution --test-args '["--self-test"]'
```

Pass arguments as an array when invoking via a programming API. With older Windows shells that alter quotes, prefer a subprocess argument array. `--allow-execution` must reflect actual user authorization to run the source/output. It is not an invitation to bypass approval. Tests execute with user permissions, not in a security sandbox. Build tools can also execute project hooks.

Repeat `--target` for additional OS/format pairs. An unavailable adapter produces an unresolved result for that target and preserves successful targets. Build-only success is `BUILT_UNTESTED`; `VERIFIED_SELECTED_TEST` covers only the explicit baseline comparison.

## Recover and continue

```powershell
Sparkitecture-Converter-CLI.exe jobs
Sparkitecture-Converter-CLI.exe job JOB_ID
Sparkitecture-Converter-CLI.exe recipes
Sparkitecture-Converter-CLI.exe handoff JOB_ID --copy-to handoff.zip
```

stdout is JSON with schema `sparkitecture.converter.v1`; progress is stderr. Exit codes: 0 completed read/build/selected-test verification, 1 error, 2 partial, 3 unresolved, 130 cancelled. Ctrl+C requests cancellation of the running process tree. `--workspace` selects a separate local store; global options precede the command.

Handoffs contain receipts/logs and a continuation instruction; they do not contain source or upload themselves. Review for local paths before sharing. Obtain permission before sending material externally. An AI can use the converter, solve independently, or combine both. Keep patches in a reviewed project copy and submit that source for another conversion. There is no automatic patch execution/import endpoint.

## Preserve the evidence

Report the job ID, output path, receipt, coverage and remaining limitations. Keep `PARTIAL`, `UNRESOLVED` and `BUILT_UNTESTED` distinct from verification. Do not promote a remembered recipe into proof: rerun it and inspect the result. Known recipes are conditioned on source hash, entrypoint, target, toolchain and test arguments.
