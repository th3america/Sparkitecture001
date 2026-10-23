# v0.1 verification

> [!WARNING]
> **SOFTWARE CONVERTER: HAS NOT BEEN LIVE TESTED. HAVE YOUR AI TEST IT BEFORE USE.**
> Development checks and sample conversions have been run; real-world use on your applications and system has not been validated.

10 focused tests passed. The packaged desktop app launched and its Sample button performed Python source inspection. The packaged CLI completed two real Windows conversions with source/output baseline comparisons; the second recognized and retested a validated recipe. A mixed-target run retained successful Windows output with an unresolved macOS handoff.

Coverage includes selected text open/edit/save/reopen and Unicode behavior, cancellation, archive traversal/collision rejection, receipts, recipe records and CLI JSON statuses. Not exhaustive equivalence or cross-platform validation.

Only the native Python/PyInstaller adapter is implemented. Other routes report unresolved work. Build/test processes use user permissions, not sandbox isolation. No automatic AI calls or external uploads. Executables match the locally tested build; release checksums accompany the downloads.
