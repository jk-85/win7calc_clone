#!/usr/bin/env python3
"""Capture real UI screens. Development only: X11 and Pillow are required."""
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
root.geometry('+60+60')

def capture(name):
    root.update()
    # A root crop retains the Tk menu bar (there is no window manager in Xvfb).
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    ImageGrab.grab(bbox=(x, max(0,y-32), x+w, y+h)).save(out/name)

for mode, expr, name in (
    ('Standard', '1234.5+67.89', 'standard.png'),
    ('Scientific', 'sin(30)+cos(60)', 'scientific.png'),
    ('Programmer', '0x1234ABCD', 'programmer.png'),
    ('Statistics', '4.5', 'statistics.png')):
    app.switch_mode(mode)
    app.calc.paste(expr)
    if mode == 'Statistics':
        app.calc.samples = [D('1.5'),D('2.25'),D('3.125'),D('4.5')]
        app.calc.statistic('mean')
    if mode == 'Programmer':
        app.base_var.set(16);app.set_base()
    app.update()
    capture(name)
app.switch_mode('Scientific');app.toggle_inverse();capture('inverse.png')
app.toggle_inverse()
app.calc.history.clear()
for expr in ('12.5+7.25','1234+5678','2^16','sqrt(2)'):
    app.calc.clear();app.calc.paste(expr);app.calc.equals()
app.history_shortcut();capture('history.png')
hist=app.history_list
# Open a real right-click menu. Crop root so the whole popup is visible.
hist.event_generate('<Button-3>', x=100, y=10,
                    rootx=hist.winfo_rootx()+160, rooty=hist.winfo_rooty()+20)
root.update()
x,y=root.winfo_rootx(),root.winfo_rooty()
ImageGrab.grab(bbox=(x, max(0,y-32), x+root.winfo_width(), y+root.winfo_height())).save(out/'history-context.png')
app.context_menu.unpost()
app.hide_history()
for aux,name in (('Unit conversion','conversion.png'),('Date calculation','dates.png'),('Mortgage','mortgage.png')):
    app.switch_aux(aux)
    if aux=='Date calculation':
        app.date_from.set('01.01.2024');app.date_to.set('01.01.2025');app.calculate_dates()
    capture(name)
root.destroy()
print(out)
