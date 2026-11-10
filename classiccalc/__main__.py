"""Command-line entry point. python3 -m classiccalc"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from . import __version__
from .engine import MODES
from .i18n import tr, normalize_input, set_language
from .platform_support import prepare_windows_process, initial_scale, tkinter_install_hint


def main() -> int:
    parser=argparse.ArgumentParser(description="Klassischer Rechner — Taschenrechner für Windows und Linux")
    parser.add_argument("--version",action="version",version=f"Klassischer Rechner {__version__}")
    parser.add_argument("--mode",choices=[mode.lower() for mode in MODES],help="anfänglicher Rechnermodus")
    parser.add_argument("--fresh",action="store_true",help="Einstellungen und Verlauf weder laden noch speichern")
    parser.add_argument("--scale",type=float,default=None,help="Oberflächenskalierung: 0.75 bis 3.0 (Standard: Windows-DPI bzw. 1)")
    parser.add_argument("--eval",metavar="EXPRESSION",help="Ausdruck ohne grafische Oberfläche berechnen")
    parser.add_argument("--smoke-test", type=Path, metavar="REPORT.json", help="Entwickler: GUI-Prüfung ohne Benutzerdaten, dann beenden")
    parser.add_argument("--language", choices=("de", "en"), default=None, help="Sprache überschreiben: de oder en")
    args=parser.parse_args()
    set_language(args.language or "de")
    if args.eval is not None:
        from .mathlib import evaluate,format_number,CalcError
        try:
            print(format_number(evaluate(normalize_input(args.eval),immediate=args.mode=="standard")))
            return 0
        except CalcError as exc:
            print(f"{'Error' if args.language == 'en' else 'Fehler'}: {tr(str(exc))}",file=sys.stderr);return 2
    if args.scale is not None and not .75<=args.scale<=3:
        parser.error("--scale muss zwischen 0.75 und 3.0 liegen")
    try:
        import tkinter as tk
        from .ui import CalculatorApp
    except ImportError:
        print("Tk fehlt. " + tkinter_install_hint(),file=sys.stderr)
        return 1
    prepare_windows_process()
    try:root=tk.Tk(className="ClassicCalc")
    except tk.TclError as exc:
        print(f"Grafische Anzeige kann nicht geöffnet werden: {exc}\nStarten Sie das Programm in einer Desktop-Sitzung.",file=sys.stderr)
        return 1
    app=CalculatorApp(root,mode=args.mode.capitalize() if args.mode else None,fresh=args.fresh or args.smoke_test is not None,scale=initial_scale(root) if args.scale is None else args.scale,language=args.language)
    if args.smoke_test is not None:
        from .smoke import run_smoke_test
        return run_smoke_test(root, app, args.smoke_test)
    root.mainloop()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
