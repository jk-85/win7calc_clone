"""Windows GUI entry point. Double-click or use Start.cmd; no console window."""
from classiccalc.launcher import gui_main

if __name__ == "__main__":
    raise SystemExit(gui_main())
