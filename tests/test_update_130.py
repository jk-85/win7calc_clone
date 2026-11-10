"""Regression coverage for 1.3.0: Standard history, navigation, and DE/EN.

Rendered alignment and event dispatch use real Tk widgets. On native Win32,
only posting the modal popup is mocked; its commands and event routing are real.
"""
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from classiccalc.i18n import (set_language, get_language, tr, display_number,
                              normalize_input, date_input_text, date_text,
                              date_duration, date_description, month_name,
                              weekday_abbreviations, shortcut_text)
from classiccalc.mathlib import D, evaluate, CalcError
from classiccalc.ui import CalculatorApp, CalendarPopup, BG
from classiccalc.tools import WORKSHEETS

ROOT = Path(__file__).resolve().parents[1]


class LanguageFormatTests(unittest.TestCase):
    def setUp(self):
        set_language('en')

    def tearDown(self):
        set_language('de')

    def test_english_labels(self):
        self.assertEqual(tr('Hide history'), 'Hide history')
        self.assertEqual(tr('Language'), 'Language')

    def test_german_labels(self):
        set_language('de')
        self.assertEqual(tr('Hide history'), 'Verlauf ausblenden')
        self.assertEqual(tr('Language'), 'Sprache')

    def test_invalid_language_rejected(self):
        with self.assertRaises(ValueError):
            set_language('xx')
        self.assertEqual(get_language(), 'en')

    def test_english_display(self):
        self.assertEqual(display_number('1,234.56'), '1,234.56')
        self.assertEqual(display_number('1.25e-20'), '1.25e-20')

    def test_english_grouped_input(self):
        for original, expected in [('1,234.56', '1234.56'), ('1,234,567', '1234567'), ('-1,234.5e-2', '-12.345')]:
            self.assertEqual(evaluate(normalize_input(original)), D(expected))

    def test_english_bad_grouping_rejected(self):
        for text in ('1,23', '12,34,567', '1,2,3', '1.2,3'):
            with self.subTest(text=text), self.assertRaises(CalcError):
                evaluate(normalize_input(text))

    def test_english_grouped_expression(self):
        self.assertEqual(evaluate(normalize_input('1,234.5 + 2.25')), D('1236.75'))
        self.assertEqual(evaluate(normalize_input('sqrt(2.25)')), D('1.5'))

    def test_locale_sensitive_ambiguity(self):
        self.assertEqual(evaluate(normalize_input('1,234')), D('1234'))
        set_language('de')
        self.assertEqual(evaluate(normalize_input('1,234')), D('1.234'))

    def test_english_dates(self):
        self.assertEqual(date_text(date(2024, 2, 29)), '2024-02-29')
        self.assertEqual(date_input_text('29.02.2024'), '2024-02-29')
        self.assertEqual(date_description(date(2024, 2, 29)), 'Thursday, 29 February 2024')

    def test_german_dates_from_canonical(self):
        set_language('de')
        self.assertEqual(date_input_text('2024-02-29'), '29.02.2024')
        self.assertEqual(date_input_text('29.02.2024'), '29.02.2024')

    def test_invalid_date_input_retained(self):
        self.assertEqual(date_input_text('unfinished'), 'unfinished')

    def test_calendar_names(self):
        self.assertEqual(month_name(3), 'March')
        self.assertEqual(weekday_abbreviations()[1], 'Tue')
        set_language('de')
        self.assertEqual(month_name(3), 'März')
        self.assertEqual(weekday_abbreviations()[1], 'Di')

    def test_duration_english(self):
        self.assertEqual(date_duration(dict(years=0, months=0, weeks=0, days=1, total_days=1)), '1 day\n\n1 day')
        self.assertIn('1,234 days', date_duration(dict(years=3, months=4, weeks=1, days=2, total_days=1234)))

    def test_accelerators(self):
        self.assertEqual(shortcut_text('Ctrl+Shift+D'), 'Ctrl+Shift+D')
        set_language('de')
        self.assertEqual(shortcut_text('Ctrl+Shift+D'), 'Strg+Umschalt+D')

    def test_cli_english_decimal(self):
        result = subprocess.run([sys.executable, str(ROOT/'app.py'), '--language', 'en', '--eval', '1,234.5+2.5'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '1237')

    def test_cli_german_decimal(self):
        result = subprocess.run([sys.executable, str(ROOT/'app.py'), '--language', 'de', '--eval', '1.234,5+2,5'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '1237')


@unittest.skipUnless(sys.platform == 'win32' or os.environ.get('DISPLAY'), 'Needs desktop or Xvfb')
class UpdateGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.app = CalculatorApp(self.root, fresh=True)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        set_language('de')
        self.assertFalse(self.errors, self.errors)

    def language(self, code):
        self.app.language_menu.invoke(0 if code == 'de' else 1)
        self.root.update()

    def populate(self, count=3):
        for value in range(1, count+1):
            self.app.calc.clear()
            self.app.calc.paste(f'{value}+0.25')
            self.app.calc.equals()
        self.app.update()

    def show(self, shortcut=False):
        if shortcut:
            widget = self.app.display_canvas
            widget.focus_force()
            self.root.update()
            widget.event_generate('<Control-h>')
        else:
            self.app.view_menu.invoke(5)
        self.root.update()
        return self.app.history_list

    def labels(self, menu):
        return [menu.entrycget(i, 'label') for i in range(menu.index('end')+1) if menu.type(i) != 'separator']

    def post(self, widget, sequence='<Button-3>'):
        widget.focus_force()
        self.root.update()
        def trigger():
            if sequence == '<Button-3>':
                widget.event_generate(sequence, x=8, y=8, rootx=80, rooty=80)
            else:
                widget.event_generate(sequence)
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            with patch.object(tk.Menu, 'tk_popup', autospec=True) as popup:
                trigger()
                self.root.update()
                popup.assert_called_once()
        else:
            trigger()
            self.root.update()
            self.assertTrue(self.app.context_menu.winfo_ismapped())
        return self.app.context_menu

    def assert_rendered_right(self, widget):
        self.root.update()
        edges = []
        index = widget.index('@0,0')
        previous = None
        while widget.compare(index, '<', 'end-1c'):
            info = widget.dlineinfo(index)
            if info is None:
                break
            if info[1] != previous and info[2] > 0:
                edges.append(info[0] + info[2])
                previous = info[1]
            index = widget.index(f'{index} +1 display lines')
        self.assertGreaterEqual(len(edges), 2, edges)
        self.assertLessEqual(max(edges)-min(edges), 1, edges)
        # Check the common right edge is actually at the pane's right margin.
        right_margin = widget.winfo_width() - int(widget.cget('padx')) - int(widget.cget('bd'))
        self.assertLessEqual(abs(edges[0]-right_margin), 2, (edges, right_margin))

    def test_standard_menu_real_alignment(self):
        self.populate()
        self.assert_rendered_right(self.show())

    def test_standard_ctrl_h_real_alignment(self):
        self.populate()
        self.assert_rendered_right(self.show(shortcut=True))

    def test_standard_selected_and_wrapped_alignment(self):
        history = self.show()
        history.set_entries(['1 = 1', '12345 + '*10 + '1 = 123451'])
        history.select_item(1)
        history.yview_moveto(1)
        self.assert_rendered_right(history)
        self.assertEqual(history.tag_cget('selected', 'justify'), 'right')

    def test_standard_both_languages_all_scales(self):
        self.populate()
        self.show()
        for language in ('en', 'de'):
            self.language(language)
            for scale in (.75, 1.0, 1.25, 1.5, 2.0, 3.0):
                with self.subTest(language=language, scale=scale):
                    self.app.change_scale(scale)
                    self.assert_rendered_right(self.app.history_list)

    def test_scientific_both_languages_alignment(self):
        self.app.switch_mode('Scientific')
        self.populate()
        self.show()
        for language in ('en', 'de'):
            self.language(language)
            self.assert_rendered_right(self.app.history_list)

    def test_standard_context_four_actions(self):
        self.populate()
        menu = self.post(self.show())
        self.assertEqual(self.labels(menu), ['Kopieren', 'Einfügen', 'Verlauf ausblenden', 'Verlauf löschen'])
        menu.invoke(0)
        self.assertEqual(self.root.clipboard_get(), '1,25')
        menu.unpost()

    def test_standard_context_empty_space(self):
        history = self.show()
        menu = self.post(history)
        self.assertEqual(menu.entrycget(0, 'state'), 'disabled')
        self.assertEqual(menu.entrycget(1, 'state'), 'normal')
        self.assertEqual(menu.entrycget(3, 'label'), 'Verlauf ausblenden')
        menu.unpost()

    def test_context_history_header_and_arrows(self):
        self.populate(15)
        self.show()
        self.app.history_list.select_item(2)
        for widget in (self.app.history_header, self.app.history_area, self.app.history_up_button, self.app.history_down_button):
            with self.subTest(widget=widget):
                menu = self.post(widget)
                self.assertEqual(self.app.history_list.curselection(), (2,))
                self.assertEqual(self.labels(menu)[-1], 'Verlauf löschen')
                menu.unpost()

    def test_context_standard_result_display(self):
        self.populate()
        self.show()
        menu = self.post(self.app.display_canvas)
        self.assertEqual(self.labels(menu)[2], 'Verlauf ausblenden')
        menu.unpost()

    def test_context_keyboard_both_locales(self):
        self.populate()
        self.show()
        for code in ('de', 'en'):
            self.language(code)
            for sequence in ('<Shift-F10>', '<Menu>'):
                menu = self.post(self.app.history_list, sequence)
                self.assertEqual(self.labels(menu)[0], 'Kopieren' if code == 'de' else 'Copy')
                menu.unpost()

    def test_arrows_upper_right_and_light(self):
        self.populate(25)
        self.show()
        up, down = self.app.history_up_button, self.app.history_down_button
        self.assertLess(up.winfo_x(), down.winfo_x())
        self.assertLessEqual(abs(down.winfo_x()+down.winfo_width()-self.app.history_header.winfo_width()), 1)
        self.assertLess(up.winfo_rooty(), self.app.history_list.winfo_rooty())
        for button in (up, down):
            self.assertEqual(button.cget('background'), BG)
            self.assertGreater(min(button.winfo_rgb(button.cget('background'))), 45000)

    def test_arrows_scroll_without_changing_calculation(self):
        self.populate(25)
        history = self.show()
        history.yview_moveto(1)
        self.root.update()
        before = history.yview()
        value, records = self.app.calc.value, deepcopy(self.app.calc.history)
        self.app.history_up_button.invoke()
        self.root.update()
        self.assertLess(history.yview()[0], before[0])
        self.app.history_down_button.invoke()
        self.root.update()
        self.assertEqual(history.yview(), before)
        self.assertEqual(self.app.calc.value, value)
        self.assertEqual(self.app.calc.history, records)

    def test_arrows_disabled_at_boundaries(self):
        self.populate(30)
        history = self.show()
        history.yview_moveto(0)
        self.root.update()
        self.assertFalse(self.app.history_up_button.enabled)
        self.assertTrue(self.app.history_down_button.enabled)
        history.yview_moveto(1)
        self.root.update()
        self.assertTrue(self.app.history_up_button.enabled)
        self.assertFalse(self.app.history_down_button.enabled)

    def test_arrows_disabled_empty_and_short_history(self):
        self.show()
        self.assertFalse(self.app.history_up_button.enabled)
        self.assertFalse(self.app.history_down_button.enabled)
        self.populate(1)
        self.root.update()
        self.assertFalse(self.app.history_up_button.enabled)
        self.assertFalse(self.app.history_down_button.enabled)

    def test_arrows_mouse_click(self):
        self.populate(30)
        history = self.show()
        history.yview_moveto(1)
        self.root.update()
        before = history.yview()[0]
        button = self.app.history_up_button
        button.event_generate('<ButtonPress-1>', x=10, y=8)
        button.event_generate('<ButtonRelease-1>', x=10, y=8)
        self.root.update()
        self.assertLess(history.yview()[0], before)

    def test_arrows_wrap_scrolls_visual_lines(self):
        history = self.show()
        history.set_entries(['1234567890 + '*40 + '1 = 1'])
        self.root.update()
        history.yview_moveto(0)
        self.root.update()
        self.assertTrue(self.app.history_down_button.enabled)
        self.app.history_down_button.invoke()
        self.root.update()
        self.assertGreater(history.yview()[0], 0)

    def test_scientific_arrows(self):
        self.app.switch_mode('Scientific')
        self.populate(30)
        history = self.show()
        before = history.yview()[0]
        self.app.history_up_button.invoke()
        self.root.update()
        self.assertLess(history.yview()[0], before)

    def test_language_menu_labels(self):
        self.assertIn('Sprache', self.labels(self.app.view_menu))
        self.assertEqual(self.labels(self.app.language_menu), ['Deutsch', 'English'])
        self.language('en')
        self.assertIn('Language', self.labels(self.app.view_menu))
        self.assertEqual(self.labels(self.app.language_menu), ['Deutsch', 'English'])

    def test_english_titles_and_menus(self):
        self.language('en')
        self.assertEqual(self.root.title(), 'Calculator')
        self.assertEqual(self.labels(self.app.menu), ['View', 'Edit', 'Help'])
        self.assertEqual(self.app.view_menu.entrycget(5, 'label'), 'History')
        self.assertEqual(self.app.view_menu.entrycget(5, 'accelerator'), 'Ctrl+H')
        self.assertEqual(self.app.language_var.get(), 'en')
        self.assertEqual(self.app.buttons['decimal'].text, '.')

    def test_english_context_actions(self):
        self.populate()
        self.show()
        self.language('en')
        menu = self.post(self.app.history_list)
        self.assertEqual(self.labels(menu), ['Copy', 'Paste', 'Hide history', 'Clear history'])
        menu.invoke(0)
        self.assertEqual(self.root.clipboard_get(), '1.25')
        self.app.put_clipboard('1,234.5 + 2.5')
        menu.invoke(1)
        self.assertEqual(self.app.calc.value, D('1237'))
        count = len(self.app.calc.history)
        menu.invoke(3)
        self.assertFalse(self.app.history_visible)
        self.assertEqual(len(self.app.calc.history), count)
        menu.unpost()

    def test_language_preserves_pending_calculation(self):
        for key in ('digit_1', 'decimal', 'digit_5', '+', 'digit_2', 'decimal', 'digit_2', 'digit_5'):
            self.app.buttons[key].invoke()
        engine = self.app.calc
        before = deepcopy(vars(engine))
        self.language('en')
        self.assertIs(self.app.calc, engine)
        self.assertEqual(vars(self.app.calc), before)
        self.app.buttons['equals'].invoke()
        self.assertEqual(self.app.calc.value, D('3.75'))
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), '3.75')
        self.language('de')
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), '3,75')

    def test_language_preserves_memory_and_history(self):
        self.populate(20)
        self.app.calc.memory_action('MS')
        self.show()
        self.app.history_list.select_item(12)
        before = deepcopy(vars(self.app.calc))
        for code in ('en', 'de', 'en'):
            self.language(code)
            self.assertEqual(vars(self.app.calc), before)
            self.assertEqual(self.app.history_list.curselection(), (12,))
            self.assertTrue(self.app.history_visible)

    def test_english_context_clear_separate_modes(self):
        self.populate()
        self.app.switch_mode('Scientific')
        self.populate(2)
        self.app.switch_mode('Standard')
        self.show()
        self.language('en')
        menu = self.app.make_context_menu(history=True)
        menu.invoke(4)
        self.assertEqual(self.app.current_history(), [])
        self.assertEqual(len(self.app.calc.history), 2)
        menu.destroy()

    def test_language_preserves_conversion_input(self):
        self.app.switch_aux('Unit conversion')
        self.app.conv_input.set('1.234,5')
        self.language('en')
        self.assertEqual(self.app.conv_input.get(), '1234.5')
        self.assertEqual(self.app.conv_source.get(), 'Meters')
        self.assertFalse(self.app.panel_error.get())
        self.language('de')
        self.assertEqual(self.app.conv_input.get(), '1234,5')
        self.assertFalse(self.app.panel_error.get())

    def test_language_translates_combobox_values(self):
        self.app.switch_aux('Unit conversion')
        self.language('en')
        from classiccalc.widgets import LocalizedCombobox
        combos = [w for w in self.app.panel.winfo_children() if isinstance(w, LocalizedCombobox)]
        self.assertTrue(any('Length' in w.cget('values') for w in combos))
        self.assertTrue(any('Meters' in w.cget('values') for w in combos))
        self.language('de')
        combos = [w for w in self.app.panel.winfo_children() if isinstance(w, LocalizedCombobox)]
        self.assertTrue(any('Länge' in w.cget('values') for w in combos))

    def test_language_preserves_dates_and_counts(self):
        self.app.switch_aux('Date calculation')
        self.app.date_from.set('01.01.2024')
        self.app.date_to.set('01.01.2025')
        self.language('en')
        self.assertEqual(self.app.date_from.get(), '2024-01-01')
        self.assertIn('366 days', self.app.date_result.get())
        self.language('de')
        self.assertEqual(self.app.date_from.get(), '01.01.2024')
        self.assertIn('366 Tage', self.app.date_result.get())

    def test_language_preserves_date_add_fields(self):
        self.app.switch_aux('Date calculation')
        self.app.date_operation.set('Add / subtract')
        self.app.rebuild_dates()
        self.app.date_from.set('31.01.2024')
        self.app.date_months.set('1')
        self.language('en')
        self.assertEqual(self.app.date_months.get(), '1')
        self.assertIn('Thursday, 29 February 2024', self.app.date_result.get())

    def test_language_preserves_worksheet(self):
        self.app.switch_aux('Mortgage')
        self.app.worksheet_inputs['purchase'].set('333.333,75')
        self.language('en')
        self.assertEqual(self.app.worksheet_inputs['purchase'].get(), '333333.75')
        self.assertFalse(self.app.panel_error.get())
        self.language('de')
        self.assertEqual(self.app.worksheet_inputs['purchase'].get(), '333333,75')
        self.assertFalse(self.app.panel_error.get())

    def test_invalid_utility_input_survives_language_switch(self):
        self.app.switch_aux('Unit conversion')
        self.app.conv_input.set('unfinished')
        self.language('en')
        self.assertEqual(self.app.conv_input.get(), 'unfinished')
        self.assertTrue(self.app.panel_error.get())

    def test_statistics_localized_and_samples_preserved(self):
        self.app.switch_mode('Statistics')
        self.app.calc.samples = [D('1.5'), D('2.5')]
        self.app.update()
        self.language('en')
        self.assertEqual(self.app.calc.samples, [D('1.5'), D('2.5')])
        self.assertEqual(self.app.stats_list.get(0, 'end'), ('1.5', '2.5'))
        self.assertEqual(self.app.display_canvas.itemcget(self.app.count_id, 'text'), 'Count = 2')
        self.assertEqual(self.app.buttons['add'].text, 'Add')

    def test_scientific_inverse_preserved(self):
        self.app.switch_mode('Scientific')
        self.app.toggle_inverse()
        self.language('en')
        self.assertTrue(self.app.inverse)
        self.assertEqual(self.app.buttons['sin'].text, 'sin⁻¹')

    def test_programmer_settings_preserved(self):
        self.app.switch_mode('Programmer')
        self.app.base_var.set(16)
        self.app.set_base()
        self.app.bits_var.set(16)
        self.app.set_word()
        self.app.calc.paste('0xABCD')
        self.app.update()
        before = deepcopy(vars(self.app.calc))
        self.language('en')
        self.assertEqual(vars(self.app.calc), before)
        self.assertIsNone(self.app.history_up_button)
        self.assertEqual(self.app.view_menu.entrycget(5, 'state'), 'disabled')

    def test_english_error_and_back(self):
        self.app.calc.set_error('Cannot divide by zero')
        self.app.update()
        self.language('en')
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), 'Cannot divide by zero')
        self.language('de')
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), 'Division durch Null nicht möglich')

    def test_english_help(self):
        self.language('en')
        self.app.show_help()
        self.root.update()
        window = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        self.assertEqual(window.title(), 'Calculator Help')
        text = window.winfo_children()[0].winfo_children()[0].get('1.0', 'end')
        self.assertIn('View > Language', text)
        self.assertIn('Clear history', text)
        window.destroy()

    def test_english_about(self):
        self.language('en')
        with patch('classiccalc.ui.messagebox.showinfo') as show:
            self.app.about()
        self.assertEqual(show.call_args.args[0], 'About Calculator')
        self.assertIn('Classic Calculator 1.3.0', show.call_args.args[1])

    def test_english_calendar(self):
        self.language('en')
        value = tk.StringVar(self.root, '2024-03-15')
        popup = CalendarPopup(self.root, value)
        self.root.update()
        labels = [w.cget('text') for w in popup.body.winfo_children() if 'text' in w.keys()]
        self.assertIn('March 2024', labels)
        self.assertIn('Tue', labels)
        popup.choose(16)
        self.assertEqual(value.get(), '2024-03-16')

    def test_all_modes_and_panels_in_english(self):
        self.language('en')
        for mode in ('Standard', 'Scientific', 'Programmer', 'Statistics'):
            self.app.switch_mode(mode)
            for panel in ('Basic', 'Unit conversion', 'Date calculation', *WORKSHEETS):
                with self.subTest(mode=mode, panel=panel):
                    self.app.switch_aux(panel)
                    self.root.update()
                    if self.app.panel_error is not None:
                        self.assertFalse(self.app.panel_error.get())

    def test_persist_language_and_restore_history(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            self.app.config_path = path
            self.app.fresh = False
            self.populate()
            self.show()
            self.language('en')
            data = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(data['language'], 'en')
            self.assertEqual(data['number_format'], 'canonical')
            self.root.destroy()
            self.root = tk.Tk()
            with patch('classiccalc.ui.settings_path', return_value=path):
                self.app = CalculatorApp(self.root)
            self.root.update()
            self.assertEqual(self.app.language, 'en')
            self.assertEqual(self.root.title(), 'Calculator')
            self.assertTrue(self.app.history_visible)
            self.assertEqual(self.app.history_list.size(), 3)
            self.assert_rendered_right(self.app.history_list)

    def test_old_settings_default_to_german(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            path.write_text('{"version":2,"mode":"Standard","history_visible":true}')
            self.root.destroy()
            self.root = tk.Tk()
            with patch('classiccalc.ui.settings_path', return_value=path):
                self.app = CalculatorApp(self.root)
            self.root.update()
            self.assertEqual(self.app.language, 'de')
            self.assertEqual(self.root.title(), 'Rechner')
            self.assertIsNotNone(self.app.history_list)

    def test_invalid_saved_language_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'state.json'
            path.write_text('{"language":"xx"}')
            self.root.destroy()
            self.root = tk.Tk()
            with patch('classiccalc.ui.settings_path', return_value=path):
                self.app = CalculatorApp(self.root)
            self.root.update()
            self.assertEqual(self.app.language, 'de')

    def test_fresh_language_change_does_not_save(self):
        with tempfile.TemporaryDirectory() as directory:
            self.app.config_path = Path(directory)/'state.json'
            self.language('en')
            self.assertFalse(self.app.config_path.exists())

    def test_constructor_language_override(self):
        self.root.destroy()
        self.root = tk.Tk()
        self.app = CalculatorApp(self.root, fresh=True, language='en')
        self.root.update()
        self.assertEqual(self.root.title(), 'Calculator')

    def test_repeated_menu_rebuilds_no_stale_callbacks(self):
        self.populate(20)
        self.show()
        for i in range(12):
            self.language('en' if i % 2 == 0 else 'de')
            self.app.history_up_button.invoke()
            self.app.history_down_button.invoke()
            self.root.update()
        self.assertEqual(self.app.history_list.size(), 20)
        self.app.hide_history()
        self.show(shortcut=True)
        self.assertEqual(self.app.history_list.size(), 20)

    def test_open_help_switches_language_live(self):
        self.app.show_help()
        self.root.update()
        window = next(iter(self.app.help_windows))
        self.assertEqual(window.title(), 'Rechner-Hilfe')
        self.language('en')
        self.assertEqual(window.title(), 'Calculator Help')
        text, close_button = self.app.help_windows[window]
        self.assertIn('HISTORY AND CLIPBOARD', text.get('1.0', 'end'))
        self.assertEqual(close_button.cget('text'), 'Close')
        window.destroy()
        self.assertFalse(self.app.help_windows)
