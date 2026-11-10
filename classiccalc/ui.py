"""Original, toolkit-native recreation of the classic calculator interface."""
from __future__ import annotations

import calendar
import json
import os
import sys
import tempfile
import traceback
from datetime import date
from decimal import DecimalException
from functools import partial
from pathlib import Path
import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox, filedialog

from . import __version__
from .platform_support import settings_path
from .i18n import (tr as _, display_number, normalize_input, LANGUAGES,
                   set_language, get_language, shortcut_text, decimal_separator,
                   month_name, weekday_abbreviations,
                   date_text, date_input_text, date_description, date_duration)
from .widgets import HistoryView, LocalizedCombobox
from .engine import Calculator, MODES
from .mathlib import D, CalcError, evaluate, format_number, number
from .tools import UNITS, WORKSHEETS, add_date, convert, date_difference, parse_date, solve_worksheet

BG = "#d9e4f1"
INK = "#172c43"
BORDER = "#8e9cad"
WHITE = "#ffffff"
BLUE = "#254d77"


def blend(a: str, b: str, t: float) -> str:
    av = [int(a[i:i+2], 16) for i in (1, 3, 5)]
    bv = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x+(y-x)*t):02x}" for x, y in zip(av, bv))


def gradient(canvas: tk.Canvas, x: int, y: int, width: int, height: int, top: str, bottom: str) -> None:
    for line in range(max(1, height)):
        canvas.create_line(x, y+line, x+width, y+line,
                           fill=blend(top, bottom, line/max(1, height-1)))


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget, self.text = widget, text
        self.timer = None
        self.window = None
        widget.bind("<Enter>", self.schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def schedule(self, event=None):
        self.hide()
        self.timer = self.widget.after(650, self.show)

    def show(self):
        self.timer = None
        if not self.widget.winfo_exists(): return
        self.window = tk.Toplevel(self.widget)
        self.window.overrideredirect(True)
        self.window.geometry(f"+{self.widget.winfo_rootx()+8}+{self.widget.winfo_rooty()+self.widget.winfo_height()+5}")
        tk.Label(self.window, text=_(self.text), background="#fffbe5", foreground=INK,
                 borderwidth=1, relief="solid", padx=6, pady=4).pack()

    def hide(self, event=None):
        if self.timer:
            try: self.widget.after_cancel(self.timer)
            except tk.TclError: pass
            self.timer = None
        if self.window:
            try: self.window.destroy()
            except tk.TclError: pass
            self.window = None


class ClassicButton(tk.Canvas):
    """A small Aero-style button, drawn from primitives (no borrowed assets)."""
    def __init__(self, parent, text, command, font, width, height,
                 kind="function", enabled=True, tooltip=""):
        super().__init__(parent, width=width, height=height, bd=0, highlightthickness=0,
                         background=BG, takefocus=1 if enabled else 0)
        self.text, self.command, self.text_font = text, command, font
        self.kind, self.enabled = kind, enabled
        self.hover = self.pressed = self.selected = False
        self.bind("<Configure>", self.draw)
        self.bind("<Enter>", self.enter)
        self.bind("<Leave>", self.leave)
        self.bind("<ButtonPress-1>", self.down)
        self.bind("<ButtonRelease-1>", self.up)
        self.bind("<FocusIn>", self.draw)
        self.bind("<FocusOut>", self.draw)
        self.bind("<space>", self.invoke)
        if tooltip: Tooltip(self, tooltip)

    def draw(self, event=None):
        if not self.winfo_exists(): return
        self.delete("all")
        w, h = max(4, self.winfo_width()), max(4, self.winfo_height())
        if not self.enabled:
            top, bottom, border, text = "#dce5ef", "#d6e1ed", "#a8b5c5", "#8190a3"
        elif self.pressed or self.selected:
            top, bottom, border, text = "#ffde95", "#ffc45b", "#c58a22", INK
        elif self.hover:
            top, bottom, border, text = "#fff6dc", "#ffdd8c", "#d4a53f", INK
        elif self.kind == "number":
            top, bottom, border, text = "#fbfdff", "#e8eef6", BORDER, INK
        elif self.kind == "equals":
            top, bottom, border, text = "#e7f2ff", "#c5d9ef", BORDER, INK
        else:
            top, bottom, border, text = "#eff5fb", "#d3dfed", BORDER, INK
        gradient(self, 2, 2, w-5, h-4, top, bottom)
        self.create_polygon(3, 1, w-4, 1, w-2, 3, w-2, h-4, w-4, h-2,
                            3, h-2, 1, h-4, 1, 3, outline=border, fill="", width=1)
        self.create_line(3, 2, w-4, 2, fill="#ffffff")
        self.create_text(w/2 + int(self.pressed), h/2 + int(self.pressed), text=_(self.text),
                         fill=text, font=self.text_font)
        if self.focus_get() == self and self.enabled:
            self.create_rectangle(4, 4, w-5, h-5, outline="#6b819b", dash=(1, 2))

    def enter(self, event=None): self.hover = True; self.draw()
    def leave(self, event=None): self.hover = self.pressed = False; self.draw()
    def down(self, event=None):
        if self.enabled:
            self.focus_set(); self.pressed = True; self.draw()
    def up(self, event):
        was_pressed = self.pressed
        self.pressed = False; self.draw()
        if self.enabled and was_pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.command()
    def invoke(self, event=None):
        if self.enabled: self.command()
        return "break"
    def set_enabled(self, enabled):
        if self.enabled != enabled:
            self.enabled = enabled; self.configure(takefocus=int(enabled)); self.draw()


class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, variable: tk.StringVar):
        super().__init__(parent)
        self.title(_("Choose a date"))
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.variable = variable
        try: self.selected = parse_date(variable.get())
        except CalcError: self.selected = date.today()
        self.year, self.month = self.selected.year, self.selected.month
        self.body = tk.Frame(self, padx=10, pady=10, bg=BG)
        self.body.pack()
        self.draw()
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()

    def move(self, offset):
        total = self.year*12+self.month-1+offset
        y, m = divmod(total, 12)
        if 1 <= y <= 9999:
            self.year, self.month = y, m+1
            self.draw()

    def choose(self, day):
        self.variable.set(date_text(date(self.year, self.month, day)))
        self.destroy()

    def draw(self):
        for child in self.body.winfo_children(): child.destroy()
        ttk.Button(self.body, text=_("‹"), width=3, command=lambda: self.move(-1)).grid(row=0, column=0)
        tk.Label(self.body, text=_(f"{month_name(self.month)} {self.year}"), bg=BG,
                 fg=INK).grid(row=0, column=1, columnspan=5)
        ttk.Button(self.body, text=_("›"), width=3, command=lambda: self.move(1)).grid(row=0, column=6)
        for c, name in enumerate(weekday_abbreviations()):
            tk.Label(self.body, text=_(name), bg=BG, fg=INK, pady=7).grid(row=1, column=c)
        for r, week in enumerate(calendar.monthcalendar(self.year, self.month), 2):
            for c, day in enumerate(week):
                if day:
                    ttk.Button(self.body, text=_(str(day)), width=3, command=partial(self.choose, day)).grid(row=r, column=c, padx=1, pady=1)
        ttk.Button(self.body, text=_("Today"), command=self.today).grid(row=9, column=0, columnspan=7, pady=(8, 0))

    def today(self):
        self.variable.set(date_text(date.today())); self.destroy()


class CalculatorApp:
    def __init__(self, root: tk.Tk, *, mode: str | None = None, fresh: bool = False,
                 scale: float = 1.0, language: str | None = None):
        self.language = "de"
        self.root, self.fresh = root, fresh
        self.scale = max(.75, min(3.0, scale))
        self.calc = Calculator()
        self.config_path = settings_path()
        self.aux = "Basic"
        self.history_visible = False
        self.inverse = False
        self.topmost = False
        self.buttons: dict[str, ClassicButton] = {}
        self.unit_state = {"category": "Length", "source": "Meters", "target": "Feet", "value": "1"}
        self.date_state = {"operation": "Difference", "from": date.today().isoformat(),
                           "to": date.today().isoformat(), "years": "0", "months": "0", "days": "0", "sign": "Add"}
        self.worksheet_state: dict[str, dict] = {}
        self.last_aux_result = None
        if not fresh: self.load_state()
        if language is not None:
            if language not in LANGUAGES:
                raise ValueError(f"Unsupported language: {language!r}")
            self.language = language
        set_language(self.language)
        if mode: self.calc.set_mode(mode)
        self.root.title(_("Calculator"))
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.option_add("*tearOff", False)
        self.root.tk.call("::msgcat::mclocale", self.language)
        self.context_menu = None
        self.help_windows = {}
        families = set(tkfont.families(root))
        self.family = next((f for f in ("Segoe UI", "Liberation Sans", "DejaVu Sans") if f in families), "TkDefaultFont")
        self.mono_family = next((f for f in ("Consolas", "Liberation Mono", "DejaVu Sans Mono") if f in families), "TkFixedFont")
        self.font = (self.family, -self.px(12))
        self.small_font = (self.family, -self.px(11))
        self.number_font = (self.family, -self.px(15))
        self.root.option_add("*Font", self.font)
        self.root.option_add("*Menu.Font", self.font)
        self.style = ttk.Style(root)
        self.style.theme_use("clam")
        self.style.configure("TCombobox", font=self.font, padding=self.px(3))
        self.style.configure("TEntry", font=self.font, padding=self.px(3))
        self.style.configure("TButton", font=self.font, padding=self.px(4))
        self.style.map("TCombobox", fieldbackground=[("readonly", WHITE)], foreground=[("readonly", INK)])
        self.language_var = tk.StringVar(root, self.language)
        self.mode_var = tk.StringVar(root, self.calc.mode)
        self.aux_var = tk.StringVar(root, self.aux)
        self.history_var = tk.BooleanVar(root, self.history_visible)
        self.group_var = tk.BooleanVar(root, self.calc.grouping)
        self.topmost_var = tk.BooleanVar(root, False)
        self.angle_var = tk.StringVar(root, self.calc.angle)
        self.base_var = tk.IntVar(root, self.calc.radix)
        self.bits_var = tk.IntVar(root, self.calc.bits)
        self.set_icon()
        self.make_menu()
        self.body = tk.Frame(root, bg=BG)
        self.body.pack()
        self.build()
        self.bind_keys()
        self.root.after_idle(self.root.focus_force)

    def px(self, x): return max(1, round(x*self.scale))

    def set_icon(self):
        # Original icon constructed procedurally; the uploaded EXE's assets are not used.
        icon = tk.PhotoImage(width=32, height=32)
        icon.put("#637f9f", to=(5, 1, 27, 31)); icon.put("#edf3f9", to=(7, 3, 25, 29))
        icon.put("#9bb7ba", to=(9, 5, 23, 12)); icon.put("#e5f3e9", to=(10, 6, 22, 11))
        for y in (15, 20, 25):
            for x in (9, 14, 19):
                icon.put("#93a8bf" if x != 19 else "#d2a354", to=(x, y, x+4, y+3))
        self.icon = icon
        self.root.iconphoto(True, icon)

    def make_menu(self):
        menu = tk.Menu(self.root, bg="#f3f3f3", activebackground="#d5e6fb", activeforeground=INK, bd=0)
        view = tk.Menu(menu)
        for i, mode in enumerate(MODES, 1):
            view.add_radiobutton(label=_(mode), variable=self.mode_var, value=mode,
                                 accelerator=f"Alt+{i}", command=partial(self.switch_mode, mode))
        view.add_separator()
        view.add_checkbutton(label=_("History"), variable=self.history_var, accelerator=shortcut_text("Ctrl+H"), command=self.toggle_history)
        view.add_checkbutton(label=_("Digit grouping"), variable=self.group_var, command=self.toggle_grouping)
        view.add_separator()
        for name, shortcut in (("Basic", "Ctrl+F4"), ("Unit conversion", "Ctrl+U"), ("Date calculation", "Ctrl+E")):
            view.add_radiobutton(label=_(name), variable=self.aux_var, value=name,
                                 accelerator=shortcut_text(shortcut), command=partial(self.switch_aux, name))
        sheets = tk.Menu(view)
        for name in WORKSHEETS:
            sheets.add_radiobutton(label=_(name), variable=self.aux_var, value=name, command=partial(self.switch_aux, name))
        view.add_cascade(label=_("Worksheets"), menu=sheets)
        view.add_separator()
        view.add_checkbutton(label=_("Always on top"), variable=self.topmost_var, command=self.toggle_topmost)
        zoom = tk.Menu(view)
        for scale in (1, 1.25, 1.5, 2):
            zoom.add_command(label=_(f"{int(scale*100)}%"), command=partial(self.change_scale, scale))
        view.add_cascade(label=_("Interface size"), menu=zoom)
        languages = tk.Menu(view)
        for code, label in LANGUAGES.items():
            languages.add_radiobutton(label=label, variable=self.language_var, value=code,
                                      command=partial(self.change_language, code))
        view.add_cascade(label=_("Language"), menu=languages)
        self.language_menu = languages
        menu.add_cascade(label=_("View"), menu=view, underline=0)
        edit = tk.Menu(menu)
        edit.add_command(label=_("Copy"), accelerator=shortcut_text("Ctrl+C"), command=self.copy)
        edit.add_command(label=_("Paste"), accelerator=shortcut_text("Ctrl+V"), command=self.paste)
        edit.add_separator()
        edit.add_command(label=_("Edit history calculation"), accelerator="F2", command=self.edit_history)
        edit.add_command(label=_("Copy history"), command=self.copy_history)
        edit.add_command(label=_("Clear history"), accelerator=shortcut_text("Ctrl+Shift+D"), command=self.clear_history)
        edit.add_separator()
        edit.add_command(label=_("Import statistics data…"), command=self.import_samples)
        edit.add_command(label=_("Export statistics data…"), command=self.export_samples)
        menu.add_cascade(label=_("Edit"), menu=edit, underline=0)
        help_menu = tk.Menu(menu)
        help_menu.add_command(label=_("View Help"), accelerator="F1", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label=_("About Calculator"), command=self.about)
        menu.add_cascade(label=_("Help"), menu=help_menu, underline=0)
        old_menu = getattr(self, "menu", None)
        self.root.config(menu=menu)
        self.menu, self.view_menu = menu, view
        if old_menu is not None:
            old_menu.destroy()

    def build(self):
        self.buttons.clear()
        for child in self.body.winfo_children(): child.destroy()
        self.history_list = self.stats_list = self.bit_canvas = None
        self.history_container = self.history_header = self.history_area = None
        self.history_up_button = self.history_down_button = None
        self.history_scrollbar = None
        self.panel_error = None
        main = tk.Frame(self.body, bg=BG, padx=self.px(10), pady=self.px(10))
        main.pack(side="left", anchor="n")
        self.bind_display_context(main)
        self.columns = 10 if self.calc.mode in ("Scientific", "Programmer") else 5
        self.cell_w, self.cell_h, self.gap = self.px(34), self.px(27), self.px(5)
        self.main_width = self.columns*self.cell_w+(self.columns-1)*self.gap
        if self.history_visible and self.calc.mode in ("Standard", "Scientific"):
            self.build_history(main)
        self.build_display(main)
        if self.calc.mode == "Programmer": self.build_bits(main)
        self.keypad = tk.Frame(main, bg=BG, width=self.main_width,
                               height=6*self.cell_h+5*self.gap)
        self.keypad.pack(pady=(self.px(6), 0))
        self.keypad.pack_propagate(False)
        if self.calc.mode == "Statistics": self.build_statistics_keys()
        else:
            offset = 5 if self.columns == 10 else 0
            self.build_standard_keys(offset)
            if self.calc.mode == "Scientific": self.build_scientific_keys()
            elif self.calc.mode == "Programmer": self.build_programmer_keys()
        if self.aux != "Basic":
            separator = tk.Frame(self.body, width=1, bg="#a5b4c8")
            separator.pack(side="left", fill="y", pady=self.px(10))
            self.panel = tk.Frame(self.body, bg=BG, padx=self.px(15), pady=self.px(12), width=self.px(330))
            self.panel.pack(side="left", fill="both", expand=True)
            if self.aux == "Unit conversion": self.build_conversion()
            elif self.aux == "Date calculation": self.build_dates()
            else: self.build_worksheet()
        self.update()
        self.root.update_idletasks()
        self.root.geometry("")

    def build_display(self, parent):
        height = self.px(145 if self.calc.mode == "Statistics" else 50)
        self.display_canvas = tk.Canvas(parent, width=self.main_width, height=height,
                                        bg=BG, bd=0, highlightthickness=0)
        self.display_canvas.pack()
        gradient(self.display_canvas, 1, 1, self.main_width-3, height-2, "#e8f0fb", WHITE)
        self.display_canvas.create_rectangle(0, 0, self.main_width-1, height-1, outline=BORDER)
        self.display_canvas.create_line(1, 1, self.main_width-2, 1, fill=WHITE)
        self.expression_id = self.display_canvas.create_text(self.main_width-self.px(6), self.px(11),
                                anchor="e", fill=INK, font=self.small_font)
        self.memory_id = self.display_canvas.create_text(self.px(7), height-self.px(10), anchor="w", fill=INK, font=self.small_font)
        self.result_font = tkfont.Font(self.root, family=self.family, size=-self.px(25))
        self.result_id = self.display_canvas.create_text(self.main_width-self.px(7), height-self.px(18),
                               anchor="e", fill="#0c1520", font=self.result_font)
        self.display_canvas.bind("<Double-Button-1>", lambda e: self.copy())
        self.bind_display_context(self.display_canvas)
        Tooltip(self.display_canvas, "Double-click to copy the result")
        if self.calc.mode == "Statistics":
            self.stats_list = tk.Listbox(self.display_canvas, bd=0, relief="flat", bg="#edf3fb",
                              fg=INK, font=self.small_font, activestyle="none", exportselection=False,
                              selectbackground="#bed6f4", selectforeground=INK)
            self.display_canvas.create_window(self.px(5), self.px(5), anchor="nw", window=self.stats_list,
                              width=self.main_width-self.px(24), height=self.px(89))
            scrollbar = ttk.Scrollbar(self.display_canvas, orient="vertical", command=self.stats_list.yview)
            self.stats_list.configure(yscrollcommand=scrollbar.set)
            self.display_canvas.create_window(self.main_width-self.px(18), self.px(5), anchor="nw", window=scrollbar,
                              width=self.px(14), height=self.px(89))
            self.count_id = self.display_canvas.create_text(self.px(6), self.px(105), anchor="w", fill=INK, font=self.small_font)
            self.stats_list.bind("<Double-Button-1>", lambda e: self.recall_sample())
            self.stats_list.bind("<Delete>", lambda e: self.delete_sample())
            self.stats_list.bind("<Button-3>", self.sample_context)
            Tooltip(self.stats_list, "Double-click: recall. Delete: remove selected sample.")

    def build_history(self, parent):
        """One shared history panel for Standard and Scientific on both OSes."""
        frame = self.history_container = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=(0, self.px(6)))
        header = self.history_header = tk.Frame(frame, bg=BG)
        header.pack(fill="x", pady=(0, self.px(3)))
        title = tk.Label(header, text=_("History"), bg=BG, fg=INK, font=self.small_font)
        title.pack(side="left")
        # Draw pale classic-style buttons instead of taking a dark system theme.
        for direction, glyph, tooltip in ((1, "▼", "Scroll history down"), (-1, "▲", "Scroll history up")):
            button = ClassicButton(header, glyph, partial(self.scroll_history, direction),
                                   self.small_font, self.px(24), self.px(20), tooltip=tooltip)
            button.pack(side="right", padx=(self.px(3), 0))
            if direction < 0:
                self.history_up_button = button
            else:
                self.history_down_button = button
        area = self.history_area = tk.Frame(frame, bg=BG)
        area.pack(fill="x")
        self.history_list = HistoryView(area, bg="#f4f8fc", fg=INK,
                                       font=self.small_font, bd=1, relief="solid",
                                       highlightthickness=0, exportselection=False,
                                       padx=self.px(6), pady=self.px(4))
        scrollbar = self.history_scrollbar = ttk.Scrollbar(area, orient="vertical", command=self.history_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.history_list.configure(yscrollcommand=self.history_scrolled)
        self.history_list.pack(side="left", fill="x", expand=True)
        self.history_list.bind("<Double-Button-1>", self.history_double_click)
        self.history_list.bind("<Return>", lambda e: self.recall_history())
        self.history_list.bind("<Delete>", lambda e: self.delete_history())
        self.history_list.bind("<F2>", lambda e: self.shortcut(self.edit_history))
        for sequence, command in (("<Control-c>", self.copy_history_result),
                                  ("<Control-v>", self.paste),
                                  ("<Control-h>", self.history_shortcut),
                                  ("<Control-H>", self.history_shortcut),
                                  ("<Control-Shift-D>", self.clear_history)):
            self.history_list.bind(sequence, lambda e, f=command: self.shortcut(f))
        row = tk.Frame(frame, bg=BG)
        row.pack(fill="x")
        for text, command in (("Edit", self.edit_history), ("Delete", self.delete_history), ("Clear", self.clear_history)):
            tk.Button(row, text=_(text), command=command, bd=0, bg=BG, fg=BLUE,
                      activebackground=BG, font=self.small_font,
                      padx=self.px(5), pady=1).pack(side="right")
        # Include the empty margins/header so a right click cannot miss the log.
        for widget in (frame, header, title, area, scrollbar, row, self.history_list,
                       self.history_up_button, self.history_down_button):
            for sequence in ("<Button-3>", "<Menu>", "<Shift-F10>"):
                widget.bind(sequence, self.history_context)

    def history_scrolled(self, first, last):
        if self.history_scrollbar is not None:
            self.history_scrollbar.set(first, last)
        if self.history_up_button is not None:
            self.history_up_button.set_enabled(float(first) > 0.000001)
        if self.history_down_button is not None:
            self.history_down_button.set_enabled(float(last) < 0.999999)

    def scroll_history(self, direction: int):
        """Scroll visual lines (including wrapped ones), never recall/delete data."""
        if self.history_list is not None:
            self.history_list.yview_scroll(-1 if direction < 0 else 1, "units")
            self.history_scrolled(*self.history_list.yview())
        return "break"

    def history_double_click(self, event):
        self.history_list.select_item(self.history_list.nearest(event.y))
        return self.recall_history()

    def button(self, key, text, row, col, callback, *, colspan=1, rowspan=1, kind="function", enabled=True, tip=""):
        width = colspan*self.cell_w+(colspan-1)*self.gap
        height = rowspan*self.cell_h+(rowspan-1)*self.gap
        font = self.number_font if kind in ("number", "equals") else self.font
        button = ClassicButton(self.keypad, text, callback, font, width, height, kind, enabled, tip)
        button.place(x=col*(self.cell_w+self.gap), y=row*(self.cell_h+self.gap), width=width, height=height)
        self.buttons[key] = button
        return button

    def command_button(self, key, text, row, col, command, *args, **kwargs):
        return self.button(key, text, row, col, partial(self.act, command, *args), **kwargs)

    def build_standard_keys(self, offset):
        for col, name in enumerate(("MC", "MR", "MS", "M+", "M-")):
            self.command_button(name, name.replace("-", "−"), 0, offset+col, self.calc.memory_action, name,
                                tip=_({"MC":"Clear memory (Ctrl+L)", "MR":"Recall memory (Ctrl+R)", "MS":"Store in memory (Ctrl+M)",
                                     "M+":"Add to memory (Ctrl+P)", "M-":"Subtract from memory (Ctrl+Q)"}[name]))
        for col, (key, label, method) in enumerate((("back", "←", self.calc.backspace), ("CE", "CE", self.calc.clear_entry),
                                                   ("C", "C", self.calc.clear), ("sign", "±", self.calc.sign))):
            self.command_button(key, label, 1, offset+col, method)
        programmer = self.calc.mode == "Programmer"
        self.command_button("sqrt", "√", 1, offset+4, self.calc.function, "sqrt", enabled=not programmer)
        for row, digits in ((2, "789"), (3, "456"), (4, "123")):
            for col, digit in enumerate(digits):
                self.command_button("digit_"+digit, digit, row, offset+col, self.calc.input_digit, digit, kind="number")
        self.command_button("digit_0", "0", 5, offset, self.calc.input_digit, "0", colspan=2, kind="number")
        self.command_button("decimal", decimal_separator(), 5, offset+2, self.calc.input_digit, ".", kind="number", enabled=not programmer)
        for row, op, text in ((2,"/","/"),(3,"*","*"),(4,"-","−"),(5,"+","+")):
            self.command_button(op, text, row, offset+3, self.calc.operator, op)
        self.command_button("percent", "%", 2, offset+4, self.calc.percent, enabled=not programmer)
        self.command_button("reciprocal", "1/x", 3, offset+4, self.calc.function, "reciprocal", enabled=not programmer)
        self.command_button("equals", "=", 4, offset+4, self.calc.equals, rowspan=2, kind="equals")

    def build_scientific_keys(self):
        row = tk.Frame(self.keypad, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        row.place(x=0, y=0, width=5*self.cell_w+4*self.gap, height=self.cell_h)
        for name, label in (("Degrees", "Degrees"), ("Radians", "Radians"), ("Gradians", "Grads")):
            tk.Radiobutton(row, text=_(label), value=name, variable=self.angle_var, command=self.set_angle,
                           bg=BG, activebackground=BG, fg=INK, font=self.small_font, padx=0, pady=0,
                           highlightthickness=0, selectcolor=WHITE).pack(side="left", expand=True)
        self.button("blank", "", 1, 0, lambda: None, enabled=False)
        self.button("inverse", "Inv", 1, 1, self.toggle_inverse, tip=_("Inverse functions (I)"))
        self.command_button("ln", "ln", 1, 2, self.scientific_function, "ln")
        self.command_button("open", "(", 1, 3, self.calc.parenthesis, False)
        self.command_button("close", ")", 1, 4, self.calc.parenthesis, True)
        matrix = [
            [("int","Int"),("sinh","sinh"),("sin","sin"),("square","x²"),("factorial","n!")],
            [("dms","dms"),("cosh","cosh"),("cos","cos"),("power","xʸ"),("root","ʸ√x")],
            [("pi","π"),("tanh","tanh"),("tan","tan"),("cube","x³"),("cuberoot","³√x")],
            [("fe","F-E"),("exponent","Exp"),("mod","Mod"),("log","log"),("pow10","10ˣ")],
        ]
        for r, cells in enumerate(matrix, 2):
            for col, (key, label) in enumerate(cells):
                if key == "fe": callback = self.toggle_fe
                elif key == "exponent": callback = partial(self.act, self.calc.exponent)
                elif key == "pi": callback = partial(self.act, self.calc.constant, "pi")
                elif key in ("power", "root", "mod"):
                    callback = partial(self.act, self.calc.operator, {"power":"^", "root":"root", "mod":"mod"}[key])
                else: callback = partial(self.act, self.scientific_function, key)
                self.button(key, label, r, col, callback)
        self.update_inverse_labels()

    def scientific_function(self, name):
        if self.inverse:
            name = {"ln":"exp", "sin":"asin", "cos":"acos", "tan":"atan", "sinh":"asinh", "cosh":"acosh",
                    "tanh":"atanh", "int":"frac", "dms":"degrees", "log":"pow10", "pow10":"log"}.get(name, name)
        self.calc.function(name)

    def toggle_inverse(self):
        self.inverse = not self.inverse
        self.update_inverse_labels()

    def update_inverse_labels(self):
        labels = {"ln":("ln","eˣ"), "sin":("sin","sin⁻¹"), "cos":("cos","cos⁻¹"), "tan":("tan","tan⁻¹"),
                  "sinh":("sinh","sinh⁻¹"), "cosh":("cosh","cosh⁻¹"), "tanh":("tanh","tanh⁻¹"),
                  "int":("Int","Frac"), "dms":("dms","deg"), "log":("log","10ˣ"), "pow10":("10ˣ","log")}
        for key, pair in labels.items():
            if key in self.buttons:
                self.buttons[key].text = pair[int(self.inverse)]
                self.buttons[key].draw()
        if "inverse" in self.buttons:
            self.buttons["inverse"].selected = self.inverse
            self.buttons["inverse"].draw()

    def build_programmer_keys(self):
        left_width = 2*self.cell_w+self.gap
        left = tk.Frame(self.keypad, bg=BG)
        left.place(x=0, y=0, width=left_width, height=6*self.cell_h+5*self.gap)
        for group, variable, items, command in (
            (0, self.base_var, (("Hex",16),("Dec",10),("Oct",8),("Bin",2)), self.set_base),
            (1, self.bits_var, (("Qword",64),("Dword",32),("Word",16),("Byte",8)), self.set_word)):
            frame = tk.Frame(left, bg=BG, highlightbackground=BORDER, highlightthickness=1)
            frame.pack(fill="both", expand=True, pady=(0, self.gap) if group == 0 else 0)
            for label, value in items:
                tk.Radiobutton(frame, text=_(label), variable=variable, value=value, command=command,
                               bg=BG, activebackground=BG, fg=INK, font=self.small_font, anchor="w", padx=2,
                               pady=0, highlightthickness=0, selectcolor=WHITE).pack(fill="x", expand=True)
        self.button("blank", "", 0, 2, lambda: None, enabled=False)
        self.command_button("mod", "Mod", 0, 3, self.calc.operator, "mod")
        self.command_button("open", "(", 1, 2, self.calc.parenthesis, False)
        self.command_button("close", ")", 1, 3, self.calc.parenthesis, True)
        for r, keys in ((2,(("rol","RoL"),("ror","RoR"))), (3,(("or","Or"),("xor","Xor"))),
                         (4,(("lsh","Lsh"),("rsh","Rsh"))), (5,(("not","Not"),("and","And")))):
            for c, (key, label) in enumerate(keys, 2):
                self.command_button(key, label, r, c, self.calc.function if key in ("rol","ror","not") else self.calc.operator, key)
        for row, letter in enumerate("ABCDEF"):
            self.command_button("digit_"+letter, letter, row, 4, self.calc.input_digit, letter)

    def build_bits(self, parent):
        height = self.px(57)
        self.bit_canvas = tk.Canvas(parent, width=self.main_width-2, height=height, bg="#dfe9f5",
                                    highlightbackground=BORDER, highlightthickness=1, bd=0)
        self.bit_canvas.pack(pady=(self.px(6),0))
        self.bit_canvas.bind("<Button-1>", self.click_bit)
        Tooltip(self.bit_canvas, "Click a bit to toggle it. Gray bits are outside the selected word size.")

    def draw_bits(self):
        if self.bit_canvas is None: return
        c = self.bit_canvas; c.delete("all")
        raw = int(self.calc.value) & self.calc.mask if not self.calc.error else 0
        group_width = (self.main_width-self.px(10))/8
        self.bit_hits = []
        for row in range(2):
            for group in range(8):
                left = self.px(5)+group*group_width
                y = self.px(10+28*row)
                digit_width = (group_width-self.px(6))/4
                for j in range(4):
                    bit = 63-row*32-group*4-j
                    x = left+(j+.5)*digit_width
                    active = bit < self.calc.bits
                    c.create_text(x, y, text=_(str((raw>>bit)&1)), font=(self.mono_family,-self.px(11)),
                                  fill=INK if active else "#a5b2c3")
                    self.bit_hits.append((x-digit_width/2, y-self.px(8), x+digit_width/2, y+self.px(8), bit))
            for col, bit in ((0,63-row*32),(4,47-row*32),(7,32-row*32)):
                x = self.px(5)+col*group_width
                if col == 7: x = self.main_width-self.px(10)
                c.create_text(x, self.px(23+28*row), text=_(str(bit)), anchor="w" if col != 7 else "e",
                              font=(self.mono_family,-self.px(10)), fill="#6d7d91")

    def click_bit(self, event):
        for x1,y1,x2,y2,bit in self.bit_hits:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.act(self.calc.toggle_bit, bit); return

    def build_statistics_keys(self):
        for col, name in enumerate(("MC","MR","MS","M+","M-")):
            self.command_button(name,name.replace("-","−"),0,col,self.calc.memory_action,name)
        self.command_button("back","←",1,0,self.calc.backspace)
        self.button("cad","CAD",1,1,self.clear_samples,tip=_("Clear all statistics data"))
        self.command_button("C","C",1,2,self.calc.clear)
        self.button("fe","F-E",1,3,self.toggle_fe)
        self.command_button("exponent","Exp",1,4,self.calc.exponent)
        for row,digits in ((2,"789"),(3,"456"),(4,"123")):
            for col,digit in enumerate(digits):
                self.command_button("digit_"+digit,digit,row,col,self.calc.input_digit,digit,kind="number")
        self.command_button("digit_0","0",5,0,self.calc.input_digit,"0",colspan=2,kind="number")
        self.command_button("decimal",decimal_separator(),5,2,self.calc.input_digit,".",kind="number")
        self.command_button("sign","±",5,3,self.calc.sign)
        self.command_button("add",_("Add sample"),5,4,self.calc.add_sample,tip=_("Add displayed value to the dataset (Enter)"))
        stats = ((2,"mean","x̄","mean_square","x̄²"),(3,"sum","Σx","sum_square","Σx²"),
                 (4,"population_sd","σₙ","sample_sd","σₙ₋₁"))
        for row,a,al,b,bl in stats:
            self.command_button(a,al,row,3,self.calc.statistic,a,tip=_(a.replace("_"," ").capitalize()))
            self.command_button(b,bl,row,4,self.calc.statistic,b,tip=_(b.replace("_"," ").capitalize()))

    def act(self, method, *args):
        try:
            method(*args)
        except (CalcError, DecimalException, OverflowError) as exc:
            self.calc.set_error(str(exc) if isinstance(exc, CalcError) else "Overflow or invalid input")
        except Exception:
            traceback.print_exc()
            self.calc.set_error("Unexpected error — see terminal")
        self.update()

    def update(self):
        if not hasattr(self, "display_canvas"): return
        text = _(self.calc.error) if self.calc.error else display_number(self.calc.display)
        available = self.main_width-self.px(27 if self.calc.memory_set else 14)
        size = self.px(25)
        while size > self.px(8):
            self.result_font.configure(size=-size)
            if self.result_font.measure(text) <= available: break
            size -= 1
        self.result_font.configure(size=-size)
        self.display_canvas.itemconfigure(self.result_id, text=_(text))
        self.display_canvas.itemconfigure(self.memory_id, text=_("M" if self.calc.memory_set else ""))
        expression = "" if self.calc.mode == "Statistics" else display_number(self.calc.expression)
        font = tkfont.Font(self.root, font=self.small_font)
        while expression and font.measure(expression) > self.main_width-self.px(12): expression = expression[1:]
        self.display_canvas.itemconfigure(self.expression_id, text=_(expression))
        if self.calc.mode == "Programmer":
            for digit in "0123456789ABCDEF":
                if "digit_"+digit in self.buttons:
                    self.buttons["digit_"+digit].set_enabled(int(digit,16) < self.calc.radix)
            self.draw_bits()
        if self.stats_list is not None:
            entries = [display_number(format_number(value)) for value in self.calc.samples]
            if tuple(entries) != self.stats_list.get(0,"end"):
                self.stats_list.delete(0,"end")
                if entries: self.stats_list.insert("end",*entries)
                self.stats_list.see("end")
            self.display_canvas.itemconfigure(self.count_id,text=_("Count = {count}").format(count=len(entries)))
        if self.history_list is not None:
            entries = [f"{display_number(item['expression'])} = {display_number(item['result'])}"
                       for item in self.current_history()]
            self.history_list.set_entries(entries)
        self.view_menu.entryconfigure(5,state="normal" if self.calc.mode in ("Standard","Scientific") else "disabled")

    def switch_mode(self, mode):
        self.remember_panel()
        self.calc.set_mode(mode); self.mode_var.set(mode)
        self.inverse = False
        self.build()

    def switch_aux(self, name):
        self.remember_panel()
        self.aux = name; self.aux_var.set(name)
        self.last_aux_result = None
        self.build()

    def toggle_history(self):
        self.history_visible = bool(self.history_var.get())
        self.remember_panel(); self.build()

    def change_language(self, language: str):
        """Rebuild presentation, retaining the engine, history, and utility inputs."""
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported language: {language!r}")
        if language == self.language:
            return
        # Normalize edited fields using the OLD locale before changing it.
        self.remember_panel()
        selection = self.history_list.curselection() if self.history_list is not None else ()
        position = self.history_list.yview()[0] if self.history_list is not None else None
        if self.context_menu is not None:
            self.context_menu.unpost()
            self.context_menu.destroy()
            self.context_menu = None
        self.language = language
        set_language(language)
        self.language_var.set(language)
        self.root.tk.call("::msgcat::mclocale", language)
        self.root.title(_("Calculator"))
        self.refresh_help_windows()
        self.make_menu()
        self.build()
        if self.history_list is not None:
            if selection:
                self.history_list.select_item(selection[0])
            if position is not None:
                self.history_list.yview_moveto(position)
        self.save_state()

    def toggle_grouping(self):
        self.calc.grouping = bool(self.group_var.get()); self.update()

    def toggle_topmost(self): self.root.attributes("-topmost", bool(self.topmost_var.get()))
    def set_angle(self): self.calc.angle = self.angle_var.get(); self.update()
    def set_base(self): self.act(self.calc.set_radix, self.base_var.get())
    def set_word(self): self.act(self.calc.set_bits, self.bits_var.get())
    def toggle_fe(self):
        self.calc.scientific_notation = not self.calc.scientific_notation
        self.calc.new_entry = True; self.update()

    def change_scale(self, scale):
        self.remember_panel(); self.save_state()
        # Reinitialize in the same process, preserving engine and utility state.
        self.scale = scale
        self.font = (self.family,-self.px(12)); self.small_font=(self.family,-self.px(11)); self.number_font=(self.family,-self.px(15))
        self.root.option_add("*Font",self.font)
        self.root.option_add("*Menu.Font",self.font)
        self.style.configure("TCombobox",font=self.font,padding=self.px(3))
        self.style.configure("TEntry",font=self.font,padding=self.px(3))
        self.style.configure("TButton",font=self.font,padding=self.px(4))
        self.make_menu(); self.build()

    def label(self, parent, text, *, heading=False, pady=(0,4)):
        widget = tk.Label(parent,text=_(text),bg=BG,fg=BLUE if heading else INK,
                          font=(self.family,-self.px(14),"bold") if heading else self.font,
                          anchor="w",justify="left",wraplength=self.px(290))
        widget.pack(fill="x",pady=tuple(self.px(v) if v else 0 for v in pady))
        return widget

    def entry(self, parent, variable, *, readonly=False):
        widget = ttk.Entry(parent,textvariable=variable,font=self.font,
                           state="readonly" if readonly else "normal")
        widget.pack(fill="x",pady=(0,self.px(6)))
        return widget

    def combo(self, parent, variable, values, command=None):
        widget = LocalizedCombobox(parent,textvariable=variable,values=list(values),state="readonly",font=self.font,width=30)
        widget.pack(fill="x",pady=(0,self.px(8)))
        if command: widget.bind("<<ComboboxSelected>>",lambda event: command())
        return widget

    def panel_buttons(self, commands):
        row = tk.Frame(self.panel,bg=BG)
        row.pack(fill="x",pady=(self.px(6),0))
        for index, (text, command) in enumerate(commands):
            ttk.Button(row, text=_(text), command=command).grid(
                row=index//2, column=index%2,
                columnspan=2 if len(commands) % 2 and index == len(commands)-1 else 1,
                sticky="ew", padx=(0, self.px(5) if index % 2 == 0 and index+1 < len(commands) else 0),
                pady=(0, self.px(4)))
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)
        return row

    def panel_message(self):
        self.panel_error = tk.StringVar(self.root,"")
        tk.Label(self.panel,textvariable=self.panel_error,bg=BG,fg="#993929",font=self.small_font,
                  wraplength=self.px(290),justify="left",anchor="w").pack(fill="x",pady=(self.px(6),0))

    def build_conversion(self):
        self.label(self.panel,"Unit conversion",heading=True,pady=(0,12))
        self.label(self.panel,"Select the type of unit you want to convert")
        state = self.unit_state
        self.conv_category = tk.StringVar(self.root,state["category"])
        self.conv_source = tk.StringVar(self.root,state["source"])
        self.conv_target = tk.StringVar(self.root,state["target"])
        self.conv_input = tk.StringVar(self.root,display_number(state["value"]))
        self.conv_output = tk.StringVar(self.root,"")
        self.converting = False
        self.combo(self.panel,self.conv_category,UNITS,self.conversion_category_changed)
        self.label(self.panel,"From")
        self.entry(self.panel,self.conv_input)
        self.conv_source_combo = self.combo(self.panel,self.conv_source,UNITS[self.conv_category.get()],self.recalculate_conversion)
        self.label(self.panel,"To",pady=(4,4))
        self.entry(self.panel,self.conv_output)
        self.conv_target_combo = self.combo(self.panel,self.conv_target,UNITS[self.conv_category.get()],self.recalculate_conversion)
        self.panel_buttons((("Use display",self.conversion_use_display),("Swap",self.conversion_swap),("Copy result",self.copy_aux)))
        self.panel_message()
        self.conv_input.trace_add("write",lambda *_: self.recalculate_conversion())
        self.conv_output.trace_add("write",lambda *_: self.recalculate_conversion(reverse=True))
        self.recalculate_conversion()

    def conversion_category_changed(self):
        options = list(UNITS[self.conv_category.get()])
        self.conv_source_combo.configure(values=options)
        self.conv_target_combo.configure(values=options)
        self.conv_source.set(options[0]); self.conv_target.set(options[min(1,len(options)-1)])
        self.recalculate_conversion()

    def recalculate_conversion(self, reverse=False):
        if self.converting: return
        self.converting = True
        try:
            source,target = self.conv_source.get(),self.conv_target.get()
            input_var,output_var = (self.conv_output,self.conv_input) if reverse else (self.conv_input,self.conv_output)
            if reverse: source,target = target,source
            value = number(normalize_input(input_var.get()))
            result = convert(value,self.conv_category.get(),source,target)
            output_var.set(display_number(format_number(result)))
            self.last_aux_result = self.conv_output.get()
            self.panel_error.set("")
        except (CalcError,DecimalException) as exc:
            output_var.set("")
            self.last_aux_result = None
            self.panel_error.set(_(str(exc)))
        finally: self.converting = False

    def conversion_use_display(self):
        if not self.calc.error: self.conv_input.set(display_number(format_number(D(self.calc.value))))

    def conversion_swap(self):
        old_output = self.conv_output.get()
        source,target = self.conv_source.get(),self.conv_target.get()
        self.conv_source.set(target); self.conv_target.set(source)
        self.conv_input.set(old_output or "0")

    def date_input(self, parent, label, variable):
        self.label(parent,label)
        row = tk.Frame(parent,bg=BG); row.pack(fill="x",pady=(0,self.px(9)))
        ttk.Entry(row,textvariable=variable,font=self.font,width=21).pack(side="left",fill="x",expand=True)
        ttk.Button(row,text=_("▦"),width=3,command=lambda: CalendarPopup(self.root,variable)).pack(side="right",padx=(self.px(5),0))

    def build_dates(self):
        self.label(self.panel,"Date calculation",heading=True,pady=(0,12))
        self.label(self.panel,"Select the date calculation you want")
        s = self.date_state
        self.date_operation = tk.StringVar(self.root,s["operation"])
        self.combo(self.panel,self.date_operation,("Difference","Add / subtract"),self.rebuild_dates)
        self.date_from = tk.StringVar(self.root,date_input_text(s["from"]))
        self.date_to = tk.StringVar(self.root,date_input_text(s["to"]))
        self.date_years = tk.StringVar(self.root,s["years"])
        self.date_months = tk.StringVar(self.root,s["months"])
        self.date_days = tk.StringVar(self.root,s["days"])
        self.date_sign = tk.StringVar(self.root,s["sign"])
        self.date_input(self.panel,"From (YYYY-MM-DD)",self.date_from)
        if self.date_operation.get() == "Difference":
            self.date_input(self.panel,"To (YYYY-MM-DD)",self.date_to)
        else:
            row = tk.Frame(self.panel,bg=BG); row.pack(fill="x",pady=(0,self.px(8)))
            for name in ("Add","Subtract"):
                tk.Radiobutton(row,text=_(name),variable=self.date_sign,value=name,bg=BG,activebackground=BG,
                               fg=INK,font=self.font,highlightthickness=0).pack(side="left")
            row = tk.Frame(self.panel,bg=BG); row.pack(fill="x")
            for label,var in (("Years",self.date_years),("Months",self.date_months),("Days",self.date_days)):
                cell=tk.Frame(row,bg=BG);cell.pack(side="left",fill="x",expand=True,padx=(0,self.px(5)))
                self.label(cell,label)
                ttk.Spinbox(cell,from_=0,to=999999,textvariable=var,width=7,font=self.font).pack(fill="x")
        self.panel_buttons((("Calculate",self.calculate_dates),("Copy result",self.copy_aux)))
        self.label(self.panel,"Result",heading=True,pady=(16,6))
        self.date_result = tk.StringVar(self.root,"")
        tk.Label(self.panel,textvariable=self.date_result,bg=BG,fg=INK,font=self.font,anchor="w",
                  justify="left",wraplength=self.px(290)).pack(fill="x")
        self.panel_message()
        self.calculate_dates()

    def rebuild_dates(self):
        self.remember_panel(); self.build()

    def calculate_dates(self):
        try:
            start = parse_date(self.date_from.get())
            if self.date_operation.get() == "Difference":
                result = date_difference(start,parse_date(self.date_to.get()))
                text = date_duration(result)
            else:
                values=[]
                for var in (self.date_years,self.date_months,self.date_days):
                    try: value=int(var.get())
                    except ValueError as exc: raise CalcError("Years, months and days must be whole numbers") from exc
                    if value<0: raise CalcError("Use Add or Subtract; enter non-negative values")
                    values.append(value)
                sign=-1 if self.date_sign.get()=="Subtract" else 1
                value=add_date(start,*(sign*v for v in values))
                text=date_description(value)+"\n"+value.isoformat()
            self.date_result.set(text); self.last_aux_result=text; self.panel_error.set("")
        except CalcError as exc:
            self.date_result.set(""); self.last_aux_result=None; self.panel_error.set(_(str(exc)))

    def build_worksheet(self):
        name=self.aux
        self.label(self.panel,name,heading=True,pady=(0,12))
        fields=WORKSHEETS[name]
        stored=self.worksheet_state.get(name,{})
        target=stored.get("target","payment" if name in ("Mortgage","Vehicle lease") else "economy")
        if target not in fields: target=list(fields)[-1]
        self.worksheet_target = tk.StringVar(self.root,fields[target])
        self.label(self.panel,"Select the value you want to calculate")
        self.combo(self.panel,self.worksheet_target,list(fields.values()),self.rebuild_worksheet)
        defaults={"purchase":"250000" if name=="Mortgage" else "30000","down":"50000","years":"30",
                  "rate":"5","payment":"1073.64" if name=="Mortgage" else "450","residual":"18000","months":"36",
                  "distance":"500","fuel":"40","economy":"8"}
        self.worksheet_inputs={}
        for key,label in fields.items():
            variable=tk.StringVar(self.root,display_number(stored.get("values",{}).get(key,defaults.get(key,"0"))))
            self.worksheet_inputs[key]=variable
            if key==target: continue
            self.label(self.panel,label)
            self.entry(self.panel,variable)
        self.panel_buttons((("Calculate",self.calculate_worksheet),("Copy result",self.copy_aux)))
        self.label(self.panel,fields[target],heading=True,pady=(14,6))
        self.worksheet_result=tk.StringVar(self.root,"")
        self.entry(self.panel,self.worksheet_result,readonly=True)
        self.panel_message()
        self.calculate_worksheet()

    def worksheet_key(self):
        return next(key for key,label in WORKSHEETS[self.aux].items() if label==self.worksheet_target.get())

    def rebuild_worksheet(self):
        self.remember_panel(); self.build()

    def calculate_worksheet(self):
        try:
            target=self.worksheet_key()
            values={key:number(normalize_input(var.get())) for key,var in self.worksheet_inputs.items() if key!=target}
            result=solve_worksheet(self.aux,target,values)
            text=display_number(format_number(result))
            self.worksheet_result.set(text)
            self.worksheet_inputs[target].set(text)
            self.last_aux_result=text;self.panel_error.set("")
        except (CalcError,DecimalException) as exc:
            self.worksheet_result.set("");self.last_aux_result=None;self.panel_error.set(_(str(exc)))

    @staticmethod
    def canonical_date(text):
        try:
            return parse_date(text).isoformat()
        except CalcError:
            return text

    def remember_panel(self):
        if self.aux=="Unit conversion" and hasattr(self,"conv_category"):
            self.unit_state={"category":self.conv_category.get(),"source":self.conv_source.get(),
                             "target":self.conv_target.get(),"value":normalize_input(self.conv_input.get())}
        elif self.aux=="Date calculation" and hasattr(self,"date_operation"):
            self.date_state={"operation":self.date_operation.get(),"from":self.canonical_date(self.date_from.get()),"to":self.canonical_date(self.date_to.get()),
                             "years":self.date_years.get(),"months":self.date_months.get(),"days":self.date_days.get(),
                             "sign":self.date_sign.get()}
        elif self.aux in WORKSHEETS and hasattr(self,"worksheet_inputs"):
            self.worksheet_state[self.aux]={"target":self.worksheet_key(),
                                         "values":{k:normalize_input(v.get()) for k,v in self.worksheet_inputs.items()}}

    def put_clipboard(self,text):
        self.root.clipboard_clear();self.root.clipboard_append(text);self.root.update_idletasks()

    def copy(self):
        if not self.calc.error: self.put_clipboard(display_number(self.calc.encode(self.calc.value)))

    def copy_aux(self):
        if self.last_aux_result is not None: self.put_clipboard(str(self.last_aux_result))

    def paste(self):
        try: text=self.root.clipboard_get()
        except tk.TclError: return
        if self.calc.mode != "Programmer":
            text = normalize_input(text)
        elif self.calc.radix == 10:
            import re
            separator = "." if self.language == "de" else ","
            pattern = r"[+-]?\d{1,3}(?:" + re.escape(separator) + r"\d{3})+"
            if re.fullmatch(pattern, text.strip()):
                text = text.replace(separator, "")
        self.act(self.calc.paste,text)

    def make_context_menu(self, *, history=False):
        """Build the same four actions for display and history, without posting."""
        menu = tk.Menu(self.root, tearoff=False)
        menu.add_command(label=_("Copy"), accelerator=shortcut_text("Ctrl+C"),
                         command=self.copy_history_result if history else self.copy,
                         state="normal" if (self.current_history() if history else not self.calc.error) else "disabled")
        menu.add_command(label=_("Paste"), accelerator=shortcut_text("Ctrl+V"), command=self.paste)
        menu.add_separator()
        supported = self.calc.mode in ("Standard", "Scientific")
        menu.add_command(label=_("Hide history" if self.history_visible else "Show history"),
                         accelerator=shortcut_text("Ctrl+H"), command=self.hide_history if self.history_visible else self.history_shortcut,
                         state="normal" if supported else "disabled")
        menu.add_command(label=_("Clear history"), accelerator=shortcut_text("Ctrl+Shift+D"), command=self.clear_history,
                         state="normal" if supported and self.current_history() else "disabled")
        return menu

    def post_context(self, menu, event):
        if self.context_menu is not None:
            self.context_menu.destroy()
        self.context_menu = menu
        if getattr(event, "num", None) == 3:
            x, y = event.x_root, event.y_root
        else:
            x, y = event.widget.winfo_rootx()+15, event.widget.winfo_rooty()+15
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
        return "break"

    def bind_display_context(self, widget):
        for sequence in ("<Button-3>", "<Menu>", "<Shift-F10>"):
            widget.bind(sequence, self.display_context)

    def display_context(self, event):
        return self.post_context(self.make_context_menu(), event)

    def history_context(self, event):
        if self.history_list is None:
            return self.display_context(event)
        if getattr(event, "num", None) == 3 and event.widget is self.history_list:
            self.history_list.select_item(self.history_list.nearest(event.y))
        self.history_list.focus_set()
        return self.post_context(self.make_context_menu(history=True), event)

    def hide_history(self):
        self.history_var.set(False)
        self.toggle_history()

    def copy_history_result(self):
        item = self.history_item()
        if item:
            self.put_clipboard(display_number(item["value"]))

    def current_history(self):
        return [item for item in self.calc.history if item.get("mode")==self.calc.mode]

    def history_item(self):
        items=self.current_history()
        if not items:return None
        selection=self.history_list.curselection() if self.history_list is not None else ()
        return items[selection[0]] if selection else items[-1]

    def recall_history(self):
        item=self.history_item()
        if item:
            self.calc.clear();self.act(self.calc.set_value,number(item["value"]))
        return "break"

    def delete_history(self):
        item=self.history_item()
        if item:self.calc.history.remove(item);self.update()
        return "break"

    def clear_history(self):
        self.calc.history[:]=[item for item in self.calc.history if item.get("mode")!=self.calc.mode]
        self.update()

    def copy_history(self):
        self.put_clipboard("\n".join(f"{display_number(item['expression'])} = {display_number(item['result'])}" for item in self.current_history()))

    def edit_history(self):
        item=self.history_item()
        if item is None or self.calc.mode not in ("Standard","Scientific"):return
        window=tk.Toplevel(self.root);window.title(_("Edit calculation"));window.transient(self.root)
        window.configure(bg=BG);window.resizable(False,False)
        frame=tk.Frame(window,bg=BG,padx=12,pady=12);frame.pack()
        tk.Label(frame,text=_("Edit the expression, then press Enter."),bg=BG,fg=INK).pack(anchor="w")
        expression=item["expression"]
        # Normalize calculator-generated unary display labels for the safe parser.
        expression=expression.replace("sqr(","square(").replace("cuberoot(","cbrt(").replace("yroot", "root")
        variable=tk.StringVar(window,display_number(expression))
        entry=ttk.Entry(frame,textvariable=variable,width=55,font=self.font);entry.pack(fill="x",pady=8)
        error=tk.StringVar(window,"");tk.Label(frame,textvariable=error,bg=BG,fg="#993929",wraplength=400).pack(fill="x")
        def commit(event=None):
            try:
                canonical = normalize_input(variable.get())
                value=evaluate(canonical,self.calc.angle,immediate=self.calc.mode=="Standard")
                item.update(expression=canonical,value=str(value),result=format_number(value))
                self.calc.clear();self.calc.set_value(value);self.update();window.destroy()
            except CalcError as exc:error.set(_(str(exc)))
            return "break"
        ttk.Button(frame,text=_("Calculate"),command=commit).pack(side="right")
        window.bind("<Return>",commit);window.bind("<Escape>",lambda e:window.destroy())
        entry.focus_set();entry.selection_range(0,"end");window.grab_set()

    def clear_samples(self):
        self.calc.samples.clear();self.update()

    def delete_sample(self):
        if self.stats_list is not None and self.stats_list.curselection():
            del self.calc.samples[self.stats_list.curselection()[0]];self.update()
        return "break"

    def recall_sample(self):
        if self.stats_list is not None and self.stats_list.curselection():
            self.act(self.calc.set_value,self.calc.samples[self.stats_list.curselection()[0]])
        return "break"

    def sample_context(self,event):
        if self.stats_list.size():self.stats_list.selection_clear(0,"end");self.stats_list.selection_set(self.stats_list.nearest(event.y))
        menu=tk.Menu(self.root);menu.add_command(label=_("Recall"),command=self.recall_sample)
        menu.add_command(label=_("Delete selected"),command=self.delete_sample)
        menu.add_command(label=_("Clear all data"),command=self.clear_samples)
        return self.post_context(menu,event)

    def import_samples(self):
        path=filedialog.askopenfilename(parent=self.root,title=_("Import statistics data"),filetypes=(("Text / CSV","*.txt *.csv"),(_("All files"),"*")))
        if not path:return
        try:
            import re
            if Path(path).stat().st_size>2_000_000:raise CalcError("File exceeds the 2 MB limit")
            text=Path(path).read_text(encoding="utf-8-sig")
            tokens=re.split(r"[;\s]+",text.strip())
            if len(tokens)>10000:raise CalcError("Maximum of 10,000 samples")
            values=[number(normalize_input(token)) for token in tokens if token]
            self.calc.samples=values;self.switch_mode("Statistics")
        except (OSError,UnicodeError,CalcError) as exc:messagebox.showerror(_("Import failed"),_(str(exc)),parent=self.root)

    def export_samples(self):
        path=filedialog.asksaveasfilename(parent=self.root,title=_("Export statistics data"),defaultextension=".csv",filetypes=(("CSV","*.csv"),("Text","*.txt")))
        if not path:return
        try:Path(path).write_text("\n".join(display_number(str(x)) for x in self.calc.samples)+"\n",encoding="utf-8")
        except OSError as exc:messagebox.showerror(_("Export failed"),_(str(exc)),parent=self.root)

    def bind_keys(self):
        self.root.bind("<KeyPress>",self.key)
        for i,mode in enumerate(MODES,1):
            self.root.bind(f"<Alt-Key-{i}>",lambda e,m=mode:self.shortcut(self.switch_mode,m))
        for sequence,func,args in (
            ("<Control-h>",self.history_shortcut,()),("<Control-u>",self.switch_aux,("Unit conversion",)),
            ("<Control-e>",self.switch_aux,("Date calculation",)),("<Control-F4>",self.switch_aux,("Basic",)),
            ("<Control-Shift-D>",self.clear_history,()),("<Control-m>",self.act,(self.calc.memory_action,"MS")),
            ("<Control-r>",self.act,(self.calc.memory_action,"MR")),("<Control-l>",self.act,(self.calc.memory_action,"MC")),
            ("<Control-p>",self.act,(self.calc.memory_action,"M+")),("<Control-q>",self.act,(self.calc.memory_action,"M-")),
            ("<Alt-c>",self.calculate_aux,()),("<F1>",self.show_help,()),("<F2>",self.f2_shortcut,())):
            self.root.bind(sequence,lambda e,f=func,a=args:self.shortcut(f,*a))
        self.root.bind("<Control-c>",self.copy_shortcut)
        self.root.bind("<Control-v>",self.paste_shortcut)
        self.root.bind("<Control-H>",lambda e:self.shortcut(self.history_shortcut))
        self.display_canvas.bind("<Menu>",self.display_context)
        self.display_canvas.bind("<Shift-F10>",self.display_context)

    def shortcut(self,func,*args):func(*args);return "break"

    def editing_widget(self,event):
        if isinstance(event.widget, HistoryView): return False
        return event.widget.winfo_class() in ("Entry","TEntry","Text","TCombobox","Spinbox","TSpinbox")

    def copy_shortcut(self,event):
        if isinstance(event.widget, HistoryView):
            self.copy_history_result(); return "break"
        if self.editing_widget(event):return None
        self.copy();return "break"

    def paste_shortcut(self,event):
        if self.editing_widget(event):return None
        self.paste();return "break"

    def f2_shortcut(self):
        if self.calc.mode == "Programmer":
            self.bits_var.set(32);self.set_word()
        else:self.edit_history()

    def history_shortcut(self):
        if self.calc.mode not in ("Standard","Scientific"):return
        self.history_var.set(not self.history_var.get());self.toggle_history()

    def calculate_aux(self):
        if self.aux=="Unit conversion":self.recalculate_conversion()
        elif self.aux=="Date calculation":self.calculate_dates()
        elif self.aux in WORKSHEETS:self.calculate_worksheet()

    def key(self,event):
        if self.editing_widget(event) or event.widget.winfo_class()=="Listbox" or isinstance(event.widget, HistoryView):return None
        char,key=event.char,event.keysym
        # German Windows AltGr emits Ctrl+Alt for @, | and ~. Allow only
        # mathematical punctuation; ordinary Ctrl/Alt shortcuts stay untouched.
        altgr_math = (sys.platform == "win32" and event.state & 0x4
                      and event.state & (0x8 | 0x20000) and char in ("@", "|", "~"))
        if event.state & (0x4 | 0x8 | (0x20000 if sys.platform == "win32" else 0)) and not altgr_math:
            return None
        if key in ("Return","KP_Enter","equal"):
            self.act(self.calc.add_sample if self.calc.mode=="Statistics" else self.calc.equals);return "break"
        if key=="Escape":self.act(self.calc.clear);return "break"
        if key=="Delete":self.act(self.calc.clear_entry);return "break"
        if key=="BackSpace":self.act(self.calc.backspace);return "break"
        if key=="F9":self.act(self.calc.sign);return "break"
        if key in ("KP_Decimal","KP_Separator") or char in (".",","):
            self.act(self.calc.input_digit,".");return "break"
        keypad={"KP_0":"0","KP_1":"1","KP_2":"2","KP_3":"3","KP_4":"4","KP_5":"5",
                "KP_6":"6","KP_7":"7","KP_8":"8","KP_9":"9","KP_Add":"+","KP_Subtract":"-",
                "KP_Multiply":"*","KP_Divide":"/"}
        char=keypad.get(key,char)
        if char and char in "0123456789":self.act(self.calc.input_digit,char);return "break"
        if self.calc.mode=="Programmer":
            if char and char.upper() in "ABCDEF":self.act(self.calc.input_digit,char);return "break"
            if key in ("F5","F6","F7","F8"):
                self.base_var.set({"F5":16,"F6":10,"F7":8,"F8":2}[key]);self.set_base();return "break"
            if key in ("F12","F2","F3","F4"):
                self.bits_var.set({"F12":64,"F2":32,"F3":16,"F4":8}[key]);self.set_word();return "break"
            mapping={"&":"and","|":"or","^":"xor","<":"lsh",">":"rsh","%":"mod"}
            if char in mapping:self.act(self.calc.operator,mapping[char]);return "break"
            if char=="~":self.act(self.calc.function,"not");return "break"
        if char and char in "+-*/" and self.calc.mode!="Statistics":self.act(self.calc.operator,char);return "break"
        if char=="(":self.act(self.calc.parenthesis,False);return "break"
        if char==")":self.act(self.calc.parenthesis,True);return "break"
        if self.calc.mode in ("Standard","Scientific"):
            if char=="%":self.act(self.calc.percent);return "break"
            if char=="@":self.act(self.calc.function,"sqrt");return "break"
            if char.lower()=="r":self.act(self.calc.function,"reciprocal");return "break"
        if self.calc.mode=="Scientific":
            functions={"s":"sin","o":"cos","t":"tan","n":"ln","l":"log","q":"square","!":"factorial",
                       "m":"dms",";":"int","#":"cube"}
            if char.lower() in functions:
                self.act(self.scientific_function,functions[char.lower()]);return "break"
            if char.lower()=="i":self.toggle_inverse();return "break"
            if char.lower()=="p":self.act(self.calc.constant,"pi");return "break"
            if char.lower() in ("y","^"):self.act(self.calc.operator,"^");return "break"
            if char.lower()=="d":self.act(self.calc.operator,"mod");return "break"
        if self.calc.mode in ("Scientific","Statistics"):
            if char.lower()=="x":self.act(self.calc.exponent);return "break"
            if char.lower()=="v":self.toggle_fe();return "break"
        if self.calc.mode=="Statistics":
            if char.lower()=="d":self.clear_samples();return "break"
            stats={"a":"mean","s":"sum","j":"sum_square","k":"population_sd","z":"sample_sd"}
            if char.lower() in stats:self.act(self.calc.statistic,stats[char.lower()]);return "break"
        return None

    def show_help(self):
        window=tk.Toplevel(self.root);window.title(_("Calculator Help"));window.transient(self.root)
        frame=tk.Frame(window,bg=BG,padx=16,pady=16);frame.pack(fill="both",expand=True)
        text=tk.Text(frame,width=75,height=29,wrap="word",font=self.font,padx=10,pady=10,bg=WHITE,fg=INK)
        text.pack(fill="both",expand=True)
        text.insert("1.0",HELP_TEXT if self.language == "de" else HELP_TEXT_EN);text.configure(state="disabled")
        close_button = ttk.Button(frame,text=_("Close"),command=window.destroy)
        close_button.pack(anchor="e",pady=(10,0))
        self.help_windows[window] = (text, close_button)
        window.bind("<Destroy>", lambda e: self.help_windows.pop(window, None) if e.widget is window else None)
        window.bind("<Escape>",lambda e:window.destroy())

    def refresh_help_windows(self):
        for window, (text, close_button) in list(self.help_windows.items()):
            if not window.winfo_exists():
                self.help_windows.pop(window, None)
                continue
            window.title(_("Calculator Help"))
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert("1.0", HELP_TEXT if self.language == "de" else HELP_TEXT_EN)
            text.configure(state="disabled")
            close_button.configure(text=_("Close"))

    def about(self):
        text = 'Eigenständig entwickelte Nachbildung des klassischen Windows-7-Rechners für Windows und Linux.\n\nPython 3 + Tk. Kein Wine und keine übernommene Rechnerdatei oder Microsoft-Grafiken. Keine Telemetrie und kein Netzwerkzugriff.\n\n60 Stellen Rechengenauigkeit; bis zu 32 angezeigte signifikante Stellen.\n64/32/16/8-Bit-Arithmetik im Zweierkomplement.\n\nKein Microsoft-Produkt. Pixelidentische Darstellung und identisches Verhalten in numerischen Grenzfällen sind nicht garantiert.' if self.language == "de" else "Independently developed recreation of the classic Windows 7 calculator for Windows and Linux.\n\nPython 3 + Tk. No Wine, Microsoft calculator binary, or Microsoft graphics. No telemetry or network access.\n\n60 working digits; up to 32 significant display digits.\n64/32/16/8-bit two's-complement arithmetic.\n\nNot a Microsoft product. Pixel-identical rendering and identical behavior in numerical edge cases are not guaranteed."
        messagebox.showinfo(_("About Calculator"), f"{_('Classic Calculator')} {__version__}\n\n{text}", parent=self.root)

    def load_state(self):
        try:
            if not self.config_path.exists() or self.config_path.stat().st_size>2_000_000:return
            state=json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(state,dict):return
            language = state.get("language", "de")
            self.language = language if language in LANGUAGES else "de"
            mode=state.get("mode")
            if mode in MODES:self.calc.mode=mode
            if state.get("angle") in ("Degrees","Radians","Gradians"):self.calc.angle=state["angle"]
            if state.get("radix") in (2,8,10,16):self.calc.radix=state["radix"]
            if state.get("bits") in (8,16,32,64):self.calc.bits=state["bits"]
            self.calc.grouping=bool(state.get("grouping",False))
            self.calc.memory=number(str(state.get("memory","0")))
            self.calc.memory_set=bool(state.get("memory_set",False))
            aux=state.get("aux","Basic")
            if aux in ("Basic","Unit conversion","Date calculation") or aux in WORKSHEETS:self.aux=aux
            self.history_visible=bool(state.get("history_visible",False))
            for item in state.get("history",[])[-200:]:
                if isinstance(item,dict) and all(isinstance(item.get(k),str) for k in ("expression","result","value","mode")):
                    if all(len(item[k])<=4096 for k in ("expression","result","value")):
                        number(item["value"]);self.calc.history.append(item)
            for value in state.get("samples",[])[:10000]:self.calc.samples.append(number(str(value)))
            unit=state.get("unit",{})
            if (isinstance(unit,dict) and unit.get("category") in UNITS
                and unit.get("source") in UNITS[unit["category"]] and unit.get("target") in UNITS[unit["category"]]
                and isinstance(unit.get("value"),str) and len(unit["value"])<=4096):
                self.unit_state = dict(unit)
                if state.get("number_format") != "canonical":
                    self.unit_state["value"] = unit["value"].replace(",", ".")
            ds=state.get("dates",{})
            if isinstance(ds,dict):
                for key in self.date_state:
                    if isinstance(ds.get(key),str) and len(ds[key])<50:self.date_state[key]=ds[key]
                if self.date_state["operation"] not in ("Difference","Add / subtract"):self.date_state["operation"]="Difference"
            ws=state.get("worksheets",{})
            if isinstance(ws,dict):
                for name,record in ws.items():
                    if name in WORKSHEETS and isinstance(record,dict) and record.get("target") in WORKSHEETS[name]:
                        values=record.get("values",{})
                        if isinstance(values,dict) and all(isinstance(v,str) and len(v)<=4096 for v in values.values()):
                            self.worksheet_state[name] = dict(record, values=dict(values))
                            if state.get("number_format") != "canonical":
                                self.worksheet_state[name]["values"] = {key: value.replace(",", "") for key, value in values.items()}
        except (OSError,ValueError,TypeError,KeyError,CalcError):
            # Invalid/corrupt settings never prevent the calculator from starting.
            pass

    def save_state(self):
        if self.fresh:return
        self.remember_panel()
        state={"version":2,"language":self.language,"number_format":"canonical","mode":self.calc.mode,"angle":self.calc.angle,"radix":self.calc.radix,"bits":self.calc.bits,
               "grouping":self.calc.grouping,"memory":str(self.calc.memory),"memory_set":self.calc.memory_set,
               "aux":self.aux,"history_visible":self.history_visible,"history":self.calc.history,"samples":[str(v) for v in self.calc.samples],
               "unit":self.unit_state,"dates":self.date_state,"worksheets":self.worksheet_state}
        temp=None
        try:
            self.config_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            with tempfile.NamedTemporaryFile("w",dir=self.config_path.parent,prefix="state-",suffix=".tmp",
                                              encoding="utf-8",delete=False) as stream:
                temp=Path(stream.name);json.dump(state,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
            temp.replace(self.config_path)
        except OSError as exc:
            print(f"{_('Could not save calculator settings')}: {exc}")
        finally:
            if temp is not None and temp.exists():
                try:temp.unlink()
                except OSError:pass

    def close(self):
        self.save_state();self.root.destroy()


HELP_TEXT = """KLASSISCHER RECHNER

Unter Ansicht > Sprache wählen Sie Deutsch oder English. Die Sprache wird ohne Neustart gewechselt und gespeichert; Zahlen-/Datumsformat, Hilfetexte und Kontextmenüs wechseln mit. Berechnung, Speicher, Verlauf und Statistikdaten bleiben erhalten. Englisch verwendet einen Dezimalpunkt und ein Komma für vollständige Tausendergruppen; für englische Datumsfelder gilt JJJJ-MM-TT. Standard ist Deutsch.

Unter Ansicht wählen Sie Standard, Wissenschaftlich, Programmierer oder Statistik. Die Zusatzbereiche für Einheitenumrechnung, Datumsberechnung und Arbeitsblätter lassen sich mit jedem Modus kombinieren.

STANDARD
Berechnungen werden direkt von links nach rechts ausgeführt: 2 + 3 × 4 = 20. Der wissenschaftliche Modus beachtet die Rangfolge und liefert hier 14. CE löscht die aktuelle Eingabe; C die Berechnung. Wiederholtes = wiederholt die letzte Operation. Bei Addition und Subtraktion verwendet % den linken Operanden als Grundwert: 200 + 10 % = 220. Bei Multiplikation und Division wird der eingegebene Operand durch 100 geteilt.

ZAHLENFORMATE
Die Anzeige und die Zwischenablage verwenden ein Dezimalkomma. Mit Zifferngruppierung wird beispielsweise 1.234,56 angezeigt. Die Eingabe 1,234 bedeutet 1,234, nicht 1234. Ein einzelner Punkt wird bei der Eingabe weiterhin als Dezimalpunkt akzeptiert (1.234 bedeutet dann 1,234); für deutsche Tausendergruppen geben Sie zusätzlich ein Dezimalkomma an, z. B. 1.234,0. Kopieren liefert den ungruppierten Wert mit voller interner Genauigkeit. Der Kommandozeilenmodus --eval gibt weiterhin einen Dezimalpunkt aus.

WISSENSCHAFTLICH
Wählen Sie Grad, Bogenmaß oder Neugrad. Inv schaltet trigonometrische, hyperbolische, logarithmische sowie Int- und dms-Funktionen um. Exp gibt einen Zehnerexponenten ein; F9 ändert dessen Vorzeichen. F-E schaltet die Exponentialdarstellung um. Klammern und Potenzen beachten die Rangfolge. dms wandelt Dezimalgrad in Grad.MinutenSekunden um; Inv + dms führt die Umkehrung aus. Es werden bis zu 32 signifikante Stellen angezeigt; intern wird mit 60 Stellen gerechnet.

PROGRAMMIERER
Hex/Dec/Oct/Bin wählen die Zahlenbasis; Qword/Dword/Word/Byte die Wortbreite 64/32/16/8 Bit. Dezimalwerte werden mit Vorzeichen angezeigt, andere Basen als Zweierkomplement-Bitmuster. Arithmetik läuft innerhalb der gewählten Wortbreite über. Division schneidet in Richtung Null ab. Rsh verschiebt logisch und füllt mit Nullen auf. RoL und RoR rotieren um ein Bit. Ein Klick in die Bitanzeige schaltet das betreffende Bit um. Unzulässige Ziffern und Gleitkommafunktionen sind deaktiviert.

STATISTIK
Geben Sie einen Wert ein und klicken Sie auf Hinz. oder drücken Sie die Eingabetaste. Ein Doppelklick übernimmt einen gespeicherten Wert; Entf löscht den ausgewählten Wert. CAD löscht alle Daten. x̄ ist der Mittelwert, x̄² der Mittelwert der Quadrate, Σx die Summe, Σx² die Quadratsumme, σₙ die Standardabweichung der Grundgesamtheit und σₙ₋₁ die Stichprobenstandardabweichung. Bearbeiten bietet Datenimport und -export. Beim Import trennen Zeilenumbrüche, Leerzeichen oder Semikolons die Werte; das Komma ist ein Dezimalzeichen, kein Spaltentrenner.

VERLAUF UND ZWISCHENABLAGE
Ansicht > Verlauf oder Strg+H zeigt bzw. verbirgt den rechtsbündigen Verlauf für den aktuellen Standard- oder wissenschaftlichen Modus. Auch lange, umgebrochene Zeilen bleiben rechtsbündig. Die hellen ▲-/▼-Tasten oben rechts blättern den Verlauf zeilenweise nach oben/unten, ohne Werte zu übernehmen. Am jeweiligen Rand sind sie deaktiviert. Ein Doppelklick oder die Eingabetaste übernimmt das Ergebnis; Pfeiltasten wählen Einträge aus. F2 bearbeitet die Berechnung. Entf löscht den ausgewählten Eintrag.

Ein Rechtsklick auf den Verlauf öffnet Kopieren, Einfügen, Verlauf ausblenden und Verlauf löschen. Kopieren übernimmt das Ergebnis des angeklickten Eintrags mit voller Genauigkeit. Einfügen übernimmt die Zwischenablage in den Rechner und verändert nicht die Verlaufszeile. Verlauf ausblenden behält die Einträge bei; Verlauf löschen bzw. Strg+Umschalt+D löscht nur den Verlauf des aktuellen Modus. Das Kontextmenü ist auch per Umschalt+F10 oder Menütaste erreichbar. Bearbeiten > Verlauf kopieren kopiert alle Berechnungen des aktuellen Modus.

Strg+C auf der Ergebnisanzeige kopiert den aktuellen Wert. Strg+V akzeptiert Zahlen oder sichere arithmetische Ausdrücke, einschließlich sin(...), sqrt(...), pi und e. Es wird kein Python-Code ausgeführt. Im Programmierermodus fügen Sie ganze Zahlen in der gewählten Basis oder mit 0x-/0o-/0b-Präfix ein.

ZUSATZFUNKTIONEN
Die Einheitenumrechnung aktualisiert sich automatisch; beide Wertefelder sind bearbeitbar. US- und UK-Volumenmaße werden ausdrücklich unterschieden. Mach verwendet einen festen Referenzwert von 340,3 m/s.

Datumsangaben werden als TT.MM.JJJJ eingegeben; JJJJ-MM-TT wird ebenfalls akzeptiert. Die Kalendertaste öffnet die Datumsauswahl. Datumsdifferenzen sind absolut. Beim Addieren von Monaten oder Jahren wird ein nicht vorhandener Tag auf den letzten gültigen Tag des Zielmonats begrenzt.

Hypotheken- und Leasingarbeitsblätter verwenden vereinfachte Monatsratenmodelle ohne Steuern, Gebühren, Versicherungen oder anbieterspezifische Regeln. Die Ergebnisse sind Rechenwerte, keine Finanzierungsangebote.

TASTATUR
Alt+1/2/3/4: Modi. Strg+U: Einheiten. Strg+E: Datum. Strg+F4: Basis. Alt+C: Zusatzbereich berechnen. Esc: C. Entf: CE. Rücktaste: Ziffer löschen. F9: Vorzeichen. Strg+M/R/L/P/Q: MS/MR/MC/M+/M−. F5/6/7/8: Hex/Dec/Oct/Bin. F12/F2/F3/F4 im Programmierermodus: Qword/Dword/Word/Byte.

Wissenschaftlich: I Umkehrfunktionen, S sin, O cos, T tan, N ln, L log, P pi, Q Quadrat, Y Potenz, D Mod, M dms, X Exp, V F-E. @ Quadratwurzel, R Kehrwert, ! Fakultät. F1: Hilfe. Ansicht > Oberflächengröße skaliert die Darstellung. Unter Windows wird beim Start die System-DPI-Skalierung verwendet; --scale setzt stattdessen eine feste Skalierung. Bei einem Wechsel auf einen Monitor mit anderer Skalierung starten Sie den Rechner neu oder wählen die Größe im Menü.

DATENSCHUTZ UND KOMPATIBILITÄT
Kein Netzwerkzugriff und keine Telemetrie. Einstellungen, Speicher, Verlauf und Statistikdaten werden unter Windows in %APPDATA%/ClassicCalc/state.json gespeichert. Unter Linux bleibt es bei ~/.config/classic-calc/state.json (bzw. XDG_CONFIG_HOME). --fresh verhindert das Lesen und Schreiben dieser Datei. Vorhandene Daten der englischen Version bleiben verwendbar.

Diese eigenständige Nachbildung enthält Microsofts Rechnerdatei weder als Bestandteil noch wird sie ausgeführt. Fensterrahmen, Schriftarten, Barrierefreiheit und numerische Grenzfälle können vom Windows-Original abweichen.
"""


HELP_TEXT_EN = """CLASSIC CALCULATOR

View > Language > Deutsch / English switches the complete interface immediately and saves the preference. Pending calculations, memory, history, samples and utility inputs are retained. A new profile defaults to German. English uses a decimal point and commas in complete thousands groups (1,234.56); German uses a decimal comma (1.234,56). Pasted numbers follow the active language. The decimal key and numeric keypad accept either decimal separator. Clipboard output is ungrouped with full internal precision. --eval always outputs a canonical decimal point.

View selects Standard, Scientific, Programmer, and Statistics. The auxiliary unit conversion, date calculation and worksheet panels work alongside any mode.

STANDARD
Calculations run immediately, left to right: 2 + 3 × 4 = 20. Scientific mode honors precedence, so the same sequence gives 14. CE clears the current entry; C clears the calculation. Repeated = repeats the last operation. For addition/subtraction, % uses the left operand as the percentage base: 200 + 10 % = 220. For multiplication/division, % divides the entered operand by 100.

SCIENTIFIC
Choose Degrees, Radians or Grads. Inv changes trigonometric, hyperbolic, logarithmic, Int and dms functions. Exp enters a base-10 exponent; F9 changes its sign. F-E toggles scientific notation. Parentheses and powers honor precedence. dms converts decimal degrees to packed degrees.minutes-seconds; Inv + dms reverses it. Up to 32 significant digits are displayed; arithmetic uses 60 working digits.

PROGRAMMER
Hex/Dec/Oct/Bin and Qword/Dword/Word/Byte select the base and 64/32/16/8-bit width. Decimal values are signed; other bases show the two's-complement bit pattern. Arithmetic wraps at the selected word width. Division truncates toward zero. Rsh is a logical zero-fill shift. RoL and RoR rotate one bit. Click the bit display to toggle a bit. Unsupported digits and floating-point functions are disabled.

STATISTICS
Enter each number, then click Add or press Enter. Double-click a sample to recall it; select it and press Delete to remove it. CAD clears the dataset. x̄ is the mean, x̄² the mean of the squared observations, Σx the sum, Σx² the sum of squares, σₙ the population standard deviation and σₙ₋₁ the sample standard deviation. Edit offers text/CSV data import and export: one number per line, or separate values by whitespace or semicolons. A comma is NOT a CSV column delimiter; in English it may form thousands groups. Exports contain one value per line.

HISTORY AND CLIPBOARD
View > History or Ctrl+H shows/hides a right-aligned log in both Standard and Scientific mode, including wrapped calculations. The pale ▲ / ▼ buttons at its top right scroll one visual line; they disable at the upper/lower boundary. They never change a calculation. Up/Down on the keyboard select records. Double-click or Enter recalls the selected result. F2 edits it; Delete removes only that record.

Right-click a history row or its empty area for Copy, Paste, Hide history, and Clear history. Shift+F10 or the Menu key also opens this menu. Copy uses the selected entry's full-precision result. Paste enters the clipboard into the calculator, not the log. Hide preserves all records; Clear or Ctrl+Shift+D removes only the active mode's records. The result display has the same menu (Show history when hidden). View > History is unavailable in Programmer and Statistics modes.

Ctrl+C on the display copies the full ungrouped value. Ctrl+V accepts numbers or safe arithmetic expressions, including sin(...), sqrt(...), pi and e. No Python code is executed. In Programmer mode, paste an integer in the selected base or with a 0x/0o/0b prefix.

UTILITIES
Unit conversion updates automatically; either value field can be edited. US and UK volumes are explicitly distinguished. Mach uses a fixed 340.3 m/s reference. English dates use YYYY-MM-DD; German dates use DD.MM.YYYY; both forms are accepted; the calendar button selects a date. Date differences are absolute, and month/year additions clamp to the last valid day of the destination month. Mortgage and lease worksheets use simplified monthly payment models, excluding taxes, fees, insurance and lender-specific rules. They are calculators, not quotations.

KEYBOARD
Alt+1/2/3/4: modes. Ctrl+U: units. Ctrl+E: dates. Ctrl+F4: basic. Alt+C: calculate the auxiliary panel. Escape: C. Delete: CE. Backspace: remove digit. F9: sign. Ctrl+M/R/L/P/Q: MS/MR/MC/M+/M−. F5/6/7/8: Hex/Dec/Oct/Bin. F12/F2/F3/F4: Qword/Dword/Word/Byte in Programmer mode. Scientific: I inverse, S sin, O cos, T tan, N ln, L log, P pi, Q square, Y power, D Mod, M dms, X Exp, V F-E. @ square root, R reciprocal, ! factorial. F1: help. View > Interface size scales the layout. On Windows, startup uses system DPI scaling unless --scale overrides it. Restart or select a size after moving to a monitor with a different scale.

PRIVACY AND COMPATIBILITY
No network access or telemetry. Preferences, memory, history and statistics are saved in %APPDATA%/ClassicCalc/state.json on Windows, or ~/.config/classic-calc/state.json (under XDG_CONFIG_HOME when set) on Linux. --fresh avoids reading or writing this file. This independent recreation does not include or execute Microsoft's calculator binary. Linux window decorations, fonts, accessibility support and edge-case numerical behavior can differ from the Windows original.
"""
