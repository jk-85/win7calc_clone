#!/usr/bin/env python3
"""Capture actual 1.3.0 widgets on X11. Development only: Pillow is required.

These are Linux/Tk captures, NOT native Windows screenshots or UI mockups.
"""
from pathlib import Path
from PIL import ImageGrab
import sys
import tkinter as tk
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classiccalc.ui import CalculatorApp
from classiccalc.mathlib import D

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]/'screenshots'
out.mkdir(parents=True, exist_ok=True)
root = tk.Tk()
app = CalculatorApp(root, fresh=True, scale=1.5)
root.geometry('+80+80')


def capture(name, *popups):
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    right, bottom = x+root.winfo_width(), y+root.winfo_height()
    top = max(0, y-32)  # Include the actual Tk menu bar, no WM decorations.
    for popup in popups:
        if popup.winfo_ismapped():
            x = min(x, popup.winfo_rootx())
            top = min(top, popup.winfo_rooty())
            right = max(right, popup.winfo_rootx()+popup.winfo_width())
            bottom = max(bottom, popup.winfo_rooty()+popup.winfo_height())
    ImageGrab.grab(bbox=(x, top, right, bottom)).save(out/name)


for mode, expr, name in (
    ('Standard', '1234.5+67.89', 'standard.png'),
    ('Scientific', 'sin(30)+cos(60)', 'scientific.png'),
    ('Programmer', '0x1234ABCD', 'programmer.png'),
    ('Statistics', '4.5', 'statistics.png')):
    app.switch_mode(mode)
    app.calc.paste(expr)
    if mode == 'Statistics':
        app.calc.samples = [D('1.5'), D('2.25'), D('3.125'), D('4.5')]
        app.calc.statistic('mean')
    if mode == 'Programmer':
        app.base_var.set(16)
        app.set_base()
    app.update()
    capture(name)
app.switch_mode('Scientific')
app.toggle_inverse()
capture('inverse.png')
app.toggle_inverse()
app.calc.history.clear()
for expr in ('12.5+7.25', '1234+5678', '2^16', 'sqrt(2)'):
    app.calc.clear()
    app.calc.paste(expr)
    app.calc.equals()
app.history_shortcut()
capture('history.png')
hist = app.history_list
hist.event_generate('<Button-3>', x=100, y=10,
                    rootx=hist.winfo_rootx()+140, rooty=hist.winfo_rooty()+20)
capture('history-context.png', app.context_menu)
app.context_menu.unpost()
app.hide_history()
for aux, name in (('Unit conversion', 'conversion.png'), ('Date calculation', 'dates.png'), ('Mortgage', 'mortgage.png')):
    app.switch_aux(aux)
    if aux == 'Date calculation':
        app.date_from.set('01.01.2024')
        app.date_to.set('01.01.2025')
        app.calculate_dates()
    capture(name)

# Explicit Standard-mode evidence for the reported issue and new navigation.
app.switch_aux('Basic')
app.switch_mode('Standard')
for expr in ('100+20', '24/3', '250*4', '7+8', '1234+5678', '1.5+2.25', '99-7', '16*8', '144/12'):
    app.calc.clear()
    app.calc.paste(expr)
    app.calc.equals()
app.history_shortcut()
app.history_list.yview("4.0")
root.update()
capture('standard-history.png')
hist = app.history_list
hist.event_generate('<Button-3>', x=20, y=10,
                    rootx=hist.winfo_rootx()+8, rooty=hist.winfo_rooty()+28)
capture('standard-history-context.png', app.context_menu)
app.context_menu.unpost()
app.change_language('en')
capture('standard-english.png')
app.change_language('de')
root.update()
app.view_menu.post(root.winfo_rootx()+3, root.winfo_rooty())
root.update()
last = app.view_menu.index('end')
app.view_menu.activate(last)
root.tk.call(app.view_menu._w, "postcascade", last)
root.update()
capture('language-menu.png', app.view_menu, app.language_menu)
app.language_menu.unpost()
app.view_menu.unpost()
root.destroy()
print(out)
