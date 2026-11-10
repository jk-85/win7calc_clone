"""German UI, real shortcut/context-menu events, and history alignment regression."""
import ast
from datetime import date
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from classiccalc.i18n import TRANSLATIONS, tr, display_number, normalize_input, date_duration
from classiccalc.mathlib import D, evaluate, CalcError
from classiccalc.tools import UNITS, WORKSHEETS, parse_date
from classiccalc.ui import CalculatorApp, CalendarPopup, HELP_TEXT
from classiccalc.widgets import HistoryView, LocalizedCombobox


class GermanFormatTests(unittest.TestCase):
    def test_decimal_and_grouping(self):
        self.assertEqual(display_number('1,234,567.89'), '1.234.567,89')
        self.assertEqual(display_number('-1.25e-10'), '-1,25e-10')

    def test_decimal_comma_not_thousands(self):
        self.assertEqual(D(normalize_input('1,234')), D('1.234'))
        self.assertEqual(D(normalize_input('123,456')), D('123.456'))

    def test_grouped_german_numbers(self):
        self.assertEqual(D(normalize_input('1.234,56')), D('1234.56'))
        self.assertEqual(D(normalize_input('-1.234.567,89')), D('-1234567.89'))
        self.assertEqual(D(normalize_input('1.234.567')), D('1234567'))

    def test_decimal_point_compatibility(self):
        self.assertEqual(D(normalize_input('1073.64')), D('1073.64'))
        self.assertEqual(D(normalize_input('1.234')), D('1.234'))

    def test_localized_expressions(self):
        self.assertEqual(evaluate(normalize_input('1,5 + 2,25')), D('3.75'))
        self.assertEqual(evaluate(normalize_input('sqrt(2,25)')), D('1.5'))
        self.assertEqual(evaluate(normalize_input('1.234,5 + 1,5')), D('1236'))
        self.assertEqual(evaluate(normalize_input('1,5e-3 + 2,5e-3')), D('.004'))

    def test_invalid_multiple_commas(self):
        with self.assertRaises(CalcError):
            evaluate(normalize_input('1,2,3'))

    def test_german_and_iso_dates(self):
        self.assertEqual(parse_date('29.02.2024'), date(2024, 2, 29))
        self.assertEqual(parse_date('2024-02-29'), date(2024, 2, 29))
        with self.assertRaises(CalcError): parse_date('29.02.2023')

    def test_date_singular_plural(self):
        self.assertEqual(date_duration(dict(years=0, months=0, weeks=0, days=1, total_days=1)), '1 Tag\n\n1 Tag')
        self.assertIn('1.234 Tage', date_duration(dict(years=3, months=4, weeks=1, days=2, total_days=1234)))

    def test_units_and_worksheet_labels_covered(self):
        for name, units in UNITS.items():
            for label in (name, *units):
                self.assertIn(label, TRANSLATIONS)
        for name, fields in WORKSHEETS.items():
            for label in (name, *fields.values()):
                self.assertIn(label, TRANSLATIONS)

    def test_engine_error_messages_covered(self):
        folder = Path(__file__).parents[1] / 'classiccalc'
        for name in ('engine.py', 'mathlib.py', 'tools.py'):
            tree = ast.parse((folder/name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'CalcError':
                    for child in ast.walk(node):
                        if isinstance(child, ast.Constant) and isinstance(child.value, str):
                            self.assertIn(child.value, TRANSLATIONS, (name, child.value))


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI tests need X11 or xvfb-run')
class GermanGuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.app = CalculatorApp(self.root, fresh=True)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.assertFalse(self.errors, f'Tk callback exceptions: {self.errors}')

    def populate(self):
        for expression in ('2+3', '1234+5678', '1.5+2.25'):
            self.app.calc.clear()
            self.app.calc.paste(expression)
            self.app.calc.equals()
        self.app.update()

    def show_history(self):
        self.populate()
        self.app.view_menu.invoke(5)
        self.root.update()
        return self.app.history_list

    def press(self, widget, sequence):
        widget.focus_force()
        self.root.update()
        widget.event_generate(sequence)
        self.root.update()

    def test_window_and_menus_german(self):
        self.assertEqual(self.root.title(), 'Rechner')
        self.assertEqual([self.app.menu.entrycget(i, 'label') for i in range(3)], ['Ansicht', 'Bearbeiten', 'Hilfe'])
        self.assertEqual([self.app.view_menu.entrycget(i, 'label') for i in range(4)], ['Standard', 'Wissenschaftlich', 'Programmierer', 'Statistik'])
        self.assertEqual(self.app.view_menu.entrycget(5, 'label'), 'Verlauf')
        self.assertEqual(self.app.buttons['decimal'].text, ',')
        self.assertIn('VERLAUF UND ZWISCHENABLAGE', HELP_TEXT)

    def test_menu_history_is_right_aligned(self):
        history = self.show_history()
        self.assertIsInstance(history, HistoryView)
        self.assertEqual(history.tag_cget('right', 'justify'), 'right')
        # Verify actual rendered geometry, not just a string configuration.
        edges = []
        for line in (1, 2, 3):
            box = history.dlineinfo(f'{line}.0')
            self.assertIsNotNone(box)
            edges.append(box[0]+box[2])
        self.assertLessEqual(max(edges)-min(edges), 1)
        self.assertIn('1,5', history.entries[-1])

    def test_ctrl_h_show_hide_and_reopen(self):
        self.populate()
        self.press(self.app.buttons['digit_1'], '<Control-h>')
        self.assertTrue(self.app.history_visible)
        self.assertEqual(self.app.history_list.tag_cget('right', 'justify'), 'right')
        self.press(self.app.history_list, '<Control-h>')
        self.assertFalse(self.app.history_visible)
        self.assertIsNone(self.app.history_list)
        self.press(self.app.display_canvas, '<Control-h>')
        self.assertEqual(self.app.history_list.size(), 3)

    def test_scientific_and_scaled_history(self):
        self.app.switch_mode('Scientific')
        self.show_history()
        for scale in (1.0, 1.25, 1.5, 2.0):
            self.app.change_scale(scale)
            self.root.update()
            self.assertEqual(self.app.history_list.size(), 3)
            self.assertEqual(self.app.history_list.tag_cget('right', 'justify'), 'right')

    def test_long_history_wraps_right_without_truncation(self):
        history = self.show_history()
        record = '1234567890 + '*14 + '1 = 17283950461'
        history.set_entries([record])
        self.root.update()
        self.assertEqual(history.get('1.0', 'end-1c'), record)
        self.assertGreater(history.count('1.0', 'end-1c', 'displaylines')[0], 1)
        self.assertEqual(history.tag_cget('right', 'justify'), 'right')

    def test_history_is_readonly(self):
        history = self.show_history()
        before = history.get('1.0', 'end-1c')
        self.press(history, '<KeyPress-7>')
        self.assertEqual(history.get('1.0', 'end-1c'), before)
        self.assertEqual(str(history.cget('state')), 'disabled')

    def test_context_exact_labels(self):
        self.show_history()
        menu = self.app.make_context_menu(history=True)
        labels = [menu.entrycget(i, 'label') for i in range(menu.index('end')+1) if menu.type(i) != 'separator']
        self.assertEqual(labels, ['Kopieren', 'Einfügen', 'Verlauf ausblenden', 'Verlauf löschen'])
        menu.destroy()

    def test_actual_right_click_posts_menu_and_selects_row(self):
        history = self.show_history()
        history.event_generate('<Button-3>', x=10, y=8, rootx=80, rooty=80)
        self.root.update()
        self.assertIsNotNone(self.app.context_menu)
        self.assertTrue(self.app.context_menu.winfo_ismapped())
        self.assertEqual(history.curselection(), (0,))
        self.app.context_menu.invoke(0)
        self.assertEqual(self.root.clipboard_get(), '5')
        self.app.context_menu.unpost()

    def test_context_copy_selected_result_not_display(self):
        history = self.show_history()
        history.selection_set(0)
        self.app.make_context_menu(history=True).invoke(0)
        self.assertEqual(self.root.clipboard_get(), '5')
        self.assertEqual(self.app.calc.value, D('3.75'))

    def test_history_ctrl_c_copies_selected_result(self):
        history = self.show_history()
        history.selection_set(0)
        self.press(history, '<Control-c>')
        self.assertEqual(self.root.clipboard_get(), '5')

    def test_context_paste_enters_calculator_not_history(self):
        history = self.show_history()
        before = history.entries
        self.app.put_clipboard('1,234 + 2,5')
        self.app.make_context_menu(history=True).invoke(1)
        self.assertEqual(self.app.calc.value, D('3.734'))
        self.assertEqual(history.entries, before)

    def test_history_ctrl_v(self):
        history = self.show_history()
        self.app.put_clipboard('12,345')
        self.press(history, '<Control-v>')
        self.assertEqual(self.app.calc.value, D('12.345'))

    def test_context_hide_preserves_entries(self):
        self.show_history()
        before = list(self.app.calc.history)
        self.app.make_context_menu(history=True).invoke(3)
        self.assertFalse(self.app.history_visible)
        self.assertFalse(self.app.history_var.get())
        self.assertEqual(self.app.calc.history, before)
        self.app.history_shortcut()
        self.assertEqual(self.app.history_list.size(), 3)

    def test_context_clear_current_mode_only(self):
        self.app.switch_mode('Scientific')
        self.populate()
        self.app.switch_mode('Standard')
        self.show_history()
        self.app.make_context_menu(history=True).invoke(4)
        self.assertEqual(self.app.history_list.size(), 0)
        self.assertEqual(len(self.app.calc.history), 3)
        self.assertTrue(all(item['mode'] == 'Scientific' for item in self.app.calc.history))
        self.assertTrue(self.app.history_visible)

    def test_clear_shortcut_when_history_focused(self):
        history = self.show_history()
        self.press(history, '<Control-Shift-D>')
        self.assertEqual(history.size(), 0)

    def test_empty_history_context(self):
        self.app.history_shortcut()
        menu = self.app.make_context_menu(history=True)
        self.assertEqual(menu.entrycget(0, 'state'), 'disabled')
        self.assertEqual(menu.entrycget(4, 'state'), 'disabled')
        menu.invoke(3)
        self.assertFalse(self.app.history_visible)

    def test_history_arrow_and_return(self):
        history = self.show_history()
        history.selection_set(1)
        self.press(history, '<Up>')
        self.assertEqual(history.curselection(), (0,))
        self.press(history, '<Return>')
        self.assertEqual(self.app.calc.value, 5)

    def test_history_delete_key_removes_selected_only(self):
        history = self.show_history()
        history.selection_set(0)
        self.press(history, '<Delete>')
        self.assertEqual(history.size(), 2)
        self.assertNotIn('2 + 3 = 5', history.entries)

    def test_context_keyboard_shortcut(self):
        history = self.show_history()
        self.press(history, '<Shift-F10>')
        self.assertTrue(self.app.context_menu.winfo_ismapped())
        self.assertEqual(self.app.context_menu.entrycget(3, 'label'), 'Verlauf ausblenden')
        self.app.context_menu.unpost()

    def test_display_context_contains_history_controls(self):
        menu = self.app.make_context_menu()
        self.assertEqual(menu.entrycget(3, 'label'), 'Verlauf einblenden')
        menu.invoke(3)
        self.assertTrue(self.app.history_visible)
        self.app.switch_mode('Programmer')
        menu = self.app.make_context_menu()
        self.assertEqual(menu.entrycget(3, 'state'), 'disabled')
        self.assertEqual(menu.entrycget(4, 'state'), 'disabled')

    def test_german_result_error_and_clipboard(self):
        self.app.calc.paste('1234.5')
        self.app.calc.grouping = True
        self.app.update()
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), '1.234,5')
        self.app.copy()
        self.assertEqual(self.root.clipboard_get(), '1234,5')
        self.app.paste()
        self.assertEqual(self.app.calc.value, D('1234.5'))
        self.app.act(self.app.calc.paste, '1/0')
        self.assertEqual(self.app.display_canvas.itemcget(self.app.result_id, 'text'), 'Division durch Null nicht möglich')

    def test_localized_combobox_maps_to_canonical(self):
        self.app.switch_aux('Unit conversion')
        combo = self.app.conv_source_combo
        self.assertEqual(combo.get(), 'Meter')
        self.assertIn('Fuß', combo.cget('values'))
        combo.set('Kilometer')
        combo.event_generate('<<ComboboxSelected>>')
        self.root.update()
        self.assertEqual(self.app.conv_source.get(), 'Kilometers')
        self.app.conv_source.set('Meters')
        self.assertEqual(combo.get(), 'Meter')

    def test_german_worksheet_and_panel_state(self):
        self.app.switch_aux('Mortgage')
        self.app.worksheet_inputs['rate'].set('5,5')
        self.app.calculate_worksheet()
        self.assertFalse(self.app.panel_error.get())
        self.assertIn(',', self.app.worksheet_result.get())
        self.app.switch_aux('Basic')
        self.app.switch_aux('Mortgage')
        self.assertEqual(self.app.worksheet_inputs['rate'].get(), '5,5')
        self.assertFalse(self.app.panel_error.get())

    def test_german_dates_and_calendar(self):
        self.app.switch_aux('Date calculation')
        self.app.date_from.set('01.01.2024')
        self.app.date_to.set('01.01.2025')
        self.app.calculate_dates()
        self.assertEqual(self.app.date_result.get(), '1 Jahr\n\n366 Tage')
        variable = tk.StringVar(self.root, '29.02.2024')
        popup = CalendarPopup(self.root, variable)
        self.root.update()
        self.assertEqual(popup.title(), 'Datum auswählen')
        popup.choose(28)
        self.assertEqual(variable.get(), '28.02.2024')

    def test_german_stats_import_export(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/'werte.csv'
            target = Path(folder)/'export.csv'
            source.write_text('1,5;2,25\n3,125', encoding='utf-8')
            with patch('classiccalc.ui.filedialog.askopenfilename', return_value=str(source)):
                self.app.import_samples()
            self.assertEqual(self.app.calc.samples, [D('1.5'), D('2.25'), D('3.125')])
            self.assertEqual(self.app.stats_list.get(0, 'end'), ('1,5', '2,25', '3,125'))
            with patch('classiccalc.ui.filedialog.asksaveasfilename', return_value=str(target)):
                self.app.export_samples()
            self.assertEqual(target.read_text(), '1,5\n2,25\n3,125\n')

    def test_old_english_settings_load_without_data_loss(self):
        state = {
            'version': 1, 'mode': 'Scientific', 'angle': 'Degrees', 'memory': '1.234', 'memory_set': True,
            'aux': 'Mortgage', 'history_visible': True, 'history': [
                {'mode': 'Scientific', 'expression': '1.5+2.25', 'result': '3.75', 'value': '3.75'}
            ], 'samples': ['1.5', '2.25'],
            'unit': {'category': 'Length', 'source': 'Meters', 'target': 'Feet', 'value': '1.234'},
            'worksheets': {'Mortgage': {'target': 'payment', 'values': {'purchase': '250000', 'down': '50000', 'years': '30', 'rate': '5.5'}}}
        }
        with tempfile.TemporaryDirectory() as folder:
            self.app.config_path = Path(folder)/'state.json'
            self.app.config_path.write_text(json.dumps(state))
            self.app.load_state()
            self.app.build()
            self.root.update()
            self.assertEqual(self.app.calc.memory, D('1.234'))
            self.assertEqual(self.app.calc.samples, [D('1.5'), D('2.25')])
            self.assertEqual(self.app.history_list.entries, ('1,5+2,25 = 3,75',))
            self.assertEqual(self.app.worksheet_inputs['rate'].get(), '5,5')
            self.app.fresh = False
            self.app.save_state()
            saved = json.loads(self.app.config_path.read_text())
            self.assertEqual(saved['worksheets']['Mortgage']['values']['rate'], '5.5')
            self.assertEqual(saved['history'], state['history'])
            self.assertEqual(saved['unit'], state['unit'])

    def test_old_grouped_worksheet_input_migrates(self):
        state = {'version': 1, 'aux': 'Mortgage', 'worksheets': {'Mortgage': {'target': 'payment',
                 'values': {'purchase': '250,000', 'down': '50,000', 'years': '30', 'rate': '5.5'}}},
                 'unit': {'category': 'Length', 'source': 'Meters', 'target': 'Feet', 'value': '1,25'}}
        with tempfile.TemporaryDirectory() as folder:
            self.app.config_path = Path(folder)/'state.json'
            self.app.config_path.write_text(json.dumps(state))
            self.app.load_state()
            self.app.build()
            self.assertEqual(self.app.worksheet_inputs['purchase'].get(), '250000')
            self.assertFalse(self.app.panel_error.get())
            self.assertEqual(self.app.unit_state['value'], '1.25')

    def test_new_canonical_state_roundtrip_no_second_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            self.app.config_path = Path(folder)/'state.json'
            self.app.fresh = False
            self.app.switch_aux('Unit conversion')
            self.app.conv_input.set('1,25')
            self.app.save_state()
            self.assertEqual(json.loads(self.app.config_path.read_text())['number_format'], 'canonical')
            self.app.load_state()
            self.app.build()
            self.assertEqual(self.app.conv_input.get(), '1,25')
            self.assertFalse(self.app.panel_error.get())
