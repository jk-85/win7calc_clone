"""Noninteractive GUI/package check, used after building on Windows."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import traceback

from . import __version__
from .mathlib import D


def run_smoke_test(root, app, output: Path) -> int:
    """Exercise real widgets without posting modal menus or changing the clipboard."""
    checks: list[str] = []
    callback_errors: list[str] = []
    root.report_callback_exception = lambda *args: callback_errors.append("".join(traceback.format_exception(*args)))

    def check(condition: bool, name: str) -> None:
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    report = {"application": "Klassischer Rechner", "version": __version__,
              "platform": sys.platform, "bits": struct.calcsize("P") * 8,
              "tcl": str(root.tk.call("info", "patchlevel")),
              "tk": str(root.tk.call("package", "provide", "Tk")), "checks": checks}
    try:
        app.change_language("de")
        root.update()
        check(root.title() == "Rechner", "German window title")
        app.switch_mode("Standard")
        for key in ("digit_2", "+", "digit_3", "*", "digit_4", "equals"):
            app.buttons[key].invoke()
        check(app.calc.value == 20, "Standard immediate arithmetic")
        app.view_menu.invoke(5)
        root.update()
        check(app.history_list is not None, "History through View menu")
        check(app.history_list.tag_cget("right", "justify") == "right", "Right-aligned Standard history")
        check(app.history_up_button is not None and app.history_down_button is not None, "Two Standard history arrows")
        check(bool(app.history_list.bind("<Button-3>")), "Standard right-click binding")
        menu = app.make_context_menu(history=True)
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1) if menu.type(i) != "separator"]
        check(labels == ["Kopieren", "Einfügen", "Verlauf ausblenden", "Verlauf löschen"], "German context-menu actions")
        before = list(app.calc.history)
        menu.invoke(3)
        check(not app.history_visible and app.calc.history == before, "Hiding history preserves records")
        menu.destroy()
        app.display_canvas.focus_force()
        root.update()
        app.display_canvas.event_generate("<Control-h>")
        root.update()
        check(app.history_visible, "Ctrl+H shows history")
        app.switch_mode("Scientific")
        for key in ("digit_2", "+", "digit_3", "*", "digit_4", "equals"):
            app.buttons[key].invoke()
        check(app.calc.value == 14, "Scientific precedence")
        app.clear_history()
        check(bool(app.calc.history) and not app.current_history(), "Clear affects only current mode")
        app.hide_history()
        app.switch_mode("Programmer")
        app.base_var.set(16)
        app.set_base()
        app.calc.paste("0xFF")
        app.update()
        check(app.calc.value == 255, "Programmer hexadecimal input")
        app.switch_mode("Statistics")
        app.calc.samples = [D("1.5"), D("2.5")]
        app.calc.statistic("mean")
        app.update()
        check(app.calc.value == 2, "Statistics mean")
        app.switch_aux("Unit conversion")
        app.conv_input.set("2")
        root.update()
        check(app.conv_output.get().startswith("6,56167"), "German unit conversion")
        app.switch_aux("Date calculation")
        app.date_from.set("01.01.2024")
        app.date_to.set("01.01.2025")
        app.calculate_dates()
        check("366 Tage" in app.date_result.get(), "German date arithmetic")
        app.switch_aux("Mortgage")
        app.calculate_worksheet()
        check(not app.panel_error.get(), "Mortgage worksheet")
        app.switch_aux("Basic")
        app.switch_mode("Standard")
        app.history_var.set(True)
        app.toggle_history()
        for value in range(20):
            app.calc.clear()
            app.calc.paste(f"{value}+0.25")
            app.calc.equals()
        app.update()
        root.update()
        before_scroll = app.history_list.yview()[0]
        app.history_up_button.invoke()
        root.update()
        check(app.history_list.yview()[0] < before_scroll, "Up arrow scrolls history")
        app.history_down_button.invoke()
        root.update()
        check(app.history_list.yview()[0] == before_scroll, "Down arrow scrolls back")
        saved_history = list(app.calc.history)
        saved_value = app.calc.value
        app.language_menu.invoke(1)
        root.update()
        check(app.language == "en" and root.title() == "Calculator", "View > Language > English")
        check(app.calc.history == saved_history and app.calc.value == saved_value, "Language preserves calculation/history")
        check(app.buttons["decimal"].text == ".", "English decimal key")
        menu = app.make_context_menu(history=True)
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1) if menu.type(i) != "separator"]
        check(labels == ["Copy", "Paste", "Hide history", "Clear history"], "English context menu")
        menu.destroy()
        app.language_menu.invoke(0)
        root.update()
        check(app.language == "de" and root.title() == "Rechner", "Return to German without restart")
        check(not callback_errors, "No Tk callback errors")
        report["ok"] = True
    except Exception:
        report["ok"] = False
        report["error"] = traceback.format_exc()
        report["callback_errors"] = callback_errors
    finally:
        root.destroy()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1
