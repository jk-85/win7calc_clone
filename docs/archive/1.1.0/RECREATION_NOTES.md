# Hinweis zur deutschen Version 1.1.0

Die Oberfläche und die Bedienungshinweise in README.md sind deutsch. Der
Verlauf ist rechtsbündig; das Kontextmenü wurde ergänzt. Rechenkern und
grundsätzliche Grenzen der ursprünglichen Nachbildung bleiben bestehen.
Die folgenden technischen Rekonstruktionsnotizen stammen aus Version 1.0.0;
der Abschnitt zur Oberflächensprache wurde aktualisiert. Sie sind keine
Behauptung einer erneuten Analyse oder eines Windows-Vergleichstests.

# Reconstruction and compatibility notes

## Input inspected

- Uploaded filename: `calc.exe`
- Size: 918,528 bytes
- SHA-256: `c6a91cba00bf87cdb064c49adaac82255cbec6fdd48fd21f9b3b96abf019916b`
- Format: PE32+, x86-64 Windows GUI executable; not a .NET assembly.
- Embedded description: Windows Calculator.
- Embedded company: Microsoft Corporation.
- Embedded file version: `6.1.7600.16385 (win7_rtm.090713-1255)`.
- Embedded original filename: `CALC.EXE`.
- PE linker timestamp: July 13, 2009, 23:57:08 UTC.

The version and resource information were read directly from the uploaded PE
file; they are not guesses based on its filename.

The executable imports Windows GUI/runtime components including USER32,
SHELL32, GDI+, UxTheme and Windows COM interfaces. It cannot be turned into a
native Linux program by renaming it or changing a launcher.

## What the file reveals

Its embedded strings identify standard/scientific/programmer/statistics state,
radix and word-length options, memory/history, trigonometric and hyperbolic
operations, unit-conversion templates, date operations and mortgage/lease/fuel
worksheets. Eleven unit-category formula identifiers are present. The PE contains
MUI metadata for en-US and image/icon/version/manifest resources, but no ordinary
RT_DIALOG, RT_MENU or RT_STRING resource tables. The separate localized
`calc.exe.mui` resource file was not uploaded.

Consequently, exact original localized layouts, strings, template constants and
all keyboard behaviors cannot be recovered from the supplied file alone. Known
Windows 7 screenshots were used as visual references for the four key layouts.
The delivered program draws its own interface and includes none of the input
executable's extracted assets.

## Implementation strategy

This is an independently written Python/Tk program. No Microsoft source code was
used or copied. No decompiled program logic is included. Decimal mathematics,
the expression parser, button state machine, conversion/date/worksheet code,
configuration handling and UI drawing were written for this reconstruction.
The Windows file itself is neither executed nor shipped in the outputs.

Tk was selected because it is available as a distribution package on Mint,
runs natively on Linux, and avoids a Windows compatibility layer, browser runtime,
proprietary fonts, or pip dependencies. The `.deb` is architecture-independent
Python and is suitable for amd64 installations. Its dependencies are `python3
(>= 3.10)` and `python3-tk`.

## Fidelity boundaries

1. **Visual fidelity is a reconstruction, not a pixel-equivalence claim.** The
   classic blue panel, display, key order, tall equals key, double-width zero,
   memory row, scientific angle row, programmer selectors/bit display and
   statistics keypad are recreated. Font metrics, radio buttons, menus, native
   Linux window decorations, DPI rounding and antialiasing differ. Aero/DWM glass
   and Windows shell integration are not emulated. Screenshots omit the native
   window-manager title bar because they were taken under Xvfb without a window
   manager.
2. **Numerical algorithms are independent.** Decimal arithmetic uses 60 working
   digits and 32 displayed digits; it is not Microsoft's original rational-number
   engine. Large-angle reduction, rounding, domains, overflow/underflow limits,
   repeated equals in complex expressions and unusual percent combinations may
   differ. The documented shift, remainder and two's-complement rules are explicit
   design choices tested by the supplied suite, not a claim of exhaustive Windows
   equivalence. `0^0` is treated as invalid input.
3. **The converter contains 97 named units in the 11 identified categories.** The
   original localized XML constants were not available. Some definitions/names
   are clarified or modernized: US/UK volumes, thermochemical calorie, IT BTU,
   the defined elementary charge for electron volts, and a stated Mach reference.
   This is not a bit-for-bit copy of the 2009 unit database.
4. **Worksheets implement explicit mathematical models.** Mortgage is a fixed
   annual nominal rate with monthly payments; lease is depreciation plus money
   factor. They exclude contract-specific costs and conventions. All displayed
   fields can be solved, including rate; this may exceed the original menu's
   solve-for options.
5. **Integration differs.** Version 1.1.0 has a German interface and uses JSON/XDG settings rather
   than the registry, and has no Windows help links, jump lists, recovery service,
   event tracing, authenticity checks or taskbar integration. Custom-drawn Tk
   buttons offer keyboard focus but do not reproduce Windows UI Automation or
   full AT-SPI screen-reader semantics.
6. **Some conveniences are additions.** Text/CSV statistics import/export, parser
   paste, explicit scale presets, always-on-top, and persistence of recent history
   are included. This recreation has no graphing or live currency conversion;
   those are not part of the identified Windows 7 feature families.

## Verification scope

The tests and screenshots were produced on x86-64 Debian 13 with Python 3.13,
Tk 8.6.16 and Xvfb. Linux Mint itself was not installed in this execution environment.
Compatibility with Mint 21.x/22.x is based on the declared Python/Tk dependencies
and avoiding newer-only Python APIs, not on a claim that the app was boot-tested
inside Mint. The original Windows executable was not run under Windows or Wine,
so **no differential or pixel-perfect comparison against the uploaded binary is
claimed**. See `TEST_REPORT.md` for actual results.

## External references consulted

The following references were consulted for compatibility, mode concepts or
visual inspection. No external program code or screenshots are bundled from them.

- Linux Mint 22 components/base: https://www.linuxmint.com/rel_wilma_whatsnew.php
- Ubuntu Noble python3-tk package: https://packages.ubuntu.com/en/noble/python3-tk
- Microsoft Calculator feature overview (current, not proof of exact 2009 behavior):
  https://github.com/microsoft/calculator/blob/main/README.md
- Windows 7 calculator screenshot reference:
  https://www.supercheats.com/windows-7/how-to/different-calculator-modes

The archived Windows 7 screenshot reference was used only to verify control
positions; it is not a source of application code. Earlier pre-release calculator
screenshots were inspected and rejected as a layout reference because they did
not match the 2009 interface.
