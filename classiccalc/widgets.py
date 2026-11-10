"""Localized combobox and a read-only, truly right-aligned history widget."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from .i18n import tr


class LocalizedCombobox(ttk.Combobox):
    """Keep stable canonical values separate from German dropdown labels."""
    def __init__(self, parent, *, textvariable, values, **kwargs):
        self.canonical = textvariable
        self.presented = tk.StringVar(parent, tr(textvariable.get()))
        self._values = list(values)
        self._syncing = False
        super().__init__(parent, textvariable=self.presented, values=[tr(v) for v in self._values], **kwargs)
        self._canonical_trace = self.canonical.trace_add("write", self._to_display)
        self._display_trace = self.presented.trace_add("write", self._from_display)

    def _to_display(self, *_):
        if self._syncing:
            return
        self._syncing = True
        try:
            self.presented.set(tr(self.canonical.get()))
        finally:
            self._syncing = False

    def _from_display(self, *_):
        if self._syncing:
            return
        shown = self.presented.get()
        value = next((v for v in self._values if tr(v) == shown), shown)
        self._syncing = True
        try:
            self.canonical.set(value)
        finally:
            self._syncing = False

    def configure(self, cnf=None, **kwargs):
        if cnf is not None and not isinstance(cnf, dict):
            return super().configure(cnf, **kwargs)
        options = dict(cnf or {}, **kwargs)
        if "values" in options:
            self._values = list(options["values"])
            options["values"] = [tr(v) for v in self._values]
        return super().configure(**options)

    config = configure

    def destroy(self):
        self.canonical.trace_remove("write", self._canonical_trace)
        self.presented.trace_remove("write", self._display_trace)
        super().destroy()


class HistoryView(tk.Text):
    """Selectable history rows, with right justification even after wrapping.

    The Text widget is permanently read-only to the user. Each history record
    is one logical paragraph, so wrapped expressions still select one record.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=1, height=5, wrap="char", state="disabled",
                         cursor="arrow", takefocus=True, undo=False, **kwargs)
        self.entries: tuple[str, ...] = ()
        self._selection: int | None = None
        self.tag_configure("right", justify="right")
        self.tag_configure("selected", background="#bed6f4", foreground="#172c43")
        self.bind("<Button-1>", self._click)
        self.bind("<B1-Motion>", lambda e: "break")
        self.bind("<Button-2>", lambda e: "break")
        self.bind("<Up>", lambda e: self._move(-1))
        self.bind("<Down>", lambda e: self._move(1))
        self.bind("<Home>", lambda e: self.select_item(0))
        self.bind("<End>", lambda e: self.select_item(self.size()-1))
        self.bind("<Prior>", lambda e: self._move(-5))
        self.bind("<Next>", lambda e: self._move(5))
        self.bind("<<Paste>>", lambda e: "break")
        self.bind("<<Cut>>", lambda e: "break")
        self.bind("<<Clear>>", lambda e: "break")

    def size(self) -> int:
        return len(self.entries)

    def curselection(self) -> tuple[int, ...]:
        return () if self._selection is None else (self._selection,)

    def set_entries(self, entries):
        entries = tuple(" ".join(text.split()) for text in entries)
        if entries == self.entries:
            return
        old_size, old_selection = self.size(), self._selection
        self.entries = entries
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.insert("1.0", "\n".join(entries), "right")
        self.tag_add("right", "1.0", "end")
        self.configure(state="disabled")
        self._selection = None
        if old_selection is not None and entries:
            self.select_item(min(old_selection, self.size()-1))
        if self.size() > old_size:
            self.see("end")

    def nearest(self, y: int) -> int:
        return min(self.size()-1, max(0, int(self.index(f"@0,{y}").split(".")[0])-1))

    def select_item(self, index: int):
        self.tag_remove("selected", "1.0", "end")
        self._selection = min(max(0, index), self.size()-1) if self.entries else None
        if self._selection is not None:
            line = self._selection+1
            self.tag_add("selected", f"{line}.0", f"{line}.end")
            self.see(f"{line}.end")
        return "break"

    def selection_set(self, index):
        return self.select_item(self.size()-1 if index == "end" else int(index))

    def _click(self, event):
        self.focus_set()
        return self.select_item(self.nearest(event.y))

    def _move(self, offset):
        index = self._selection if self._selection is not None else self.size()-1
        return self.select_item(index+offset)
