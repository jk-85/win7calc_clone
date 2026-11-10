"""Run on a desktop or with xvfb-run -a python3 -m unittest tests.test_gui -v."""
import json
import os
from pathlib import Path
import tempfile
import unittest
import tkinter as tk
from classiccalc.ui import CalculatorApp
from classiccalc.mathlib import D
from classiccalc.i18n import normalize_input
from classiccalc.tools import WORKSHEETS


@unittest.skipUnless(os.environ.get('DISPLAY'), 'GUI tests need a display (use xvfb-run -a)')
class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.errors=[]
        self.root.report_callback_exception=lambda *args:self.errors.append(args)
        self.app=CalculatorApp(self.root,fresh=True)
        self.root.update()
    def tearDown(self):
        self.root.destroy()
        self.assertFalse(self.errors,f'Tk callback exceptions: {self.errors}')
    def click(self,key):
        self.app.buttons[key].invoke();self.root.update()
    def test_standard_buttons(self):
        for key in ('digit_2','+','digit_3','*','digit_4','equals'):self.click(key)
        self.assertEqual(self.app.calc.value,20)
    def test_scientific_buttons(self):
        self.app.switch_mode('Scientific')
        for key in ('digit_2','+','digit_3','*','digit_4','equals'):self.click(key)
        self.assertEqual(self.app.calc.value,14)
    def test_inverse_sine(self):
        self.app.switch_mode('Scientific')
        for key in ('digit_0','decimal','digit_5','inverse','sin'):self.click(key)
        self.assertLess(abs(self.app.calc.value-30),D('1e-45'))
    def test_programmer_disable_digits(self):
        self.app.switch_mode('Programmer');self.app.base_var.set(2);self.app.set_base()
        self.assertFalse(self.app.buttons['digit_2'].enabled)
        self.assertFalse(self.app.buttons['sqrt'].enabled)
        self.assertTrue(self.app.buttons['digit_1'].enabled)
    def test_programmer_word_shortcut(self):
        self.app.switch_mode('Programmer');self.app.f2_shortcut();self.assertEqual(self.app.calc.bits,32)
    def test_bit_display(self):
        self.app.switch_mode('Programmer');self.root.update()
        self.assertEqual(len(self.app.bit_hits),64)
        hit=self.app.bit_hits[-1]
        from types import SimpleNamespace
        self.app.click_bit(SimpleNamespace(x=(hit[0]+hit[2])/2,y=(hit[1]+hit[3])/2))
        self.assertEqual(self.app.calc.value,1)
    def test_statistics_buttons(self):
        self.app.switch_mode('Statistics')
        for key in ('digit_2','add','digit_4','add','digit_6','add','mean'):self.click(key)
        self.assertEqual(self.app.calc.value,4);self.assertEqual(self.app.stats_list.size(),3)
    def test_history_recall(self):
        for key in ('digit_2','+','digit_3','equals'):self.click(key)
        self.app.history_shortcut();self.root.update();self.assertEqual(self.app.history_list.size(),1)
        self.app.calc.clear();self.app.recall_history();self.assertEqual(self.app.calc.value,5)
    def test_history_mode_separate(self):
        for key in ('digit_2','+','digit_3','equals'):self.click(key)
        self.app.history_shortcut();self.app.switch_mode('Scientific');self.assertEqual(self.app.history_list.size(),0)
    def test_unit_conversion_forward(self):
        self.app.switch_aux('Unit conversion');self.app.conv_input.set('2')
        self.assertFalse(self.app.panel_error.get());self.assertTrue(self.app.conv_output.get().startswith('6,56167'))
    def test_unit_conversion_reverse(self):
        self.app.switch_aux('Unit conversion');self.app.conv_output.set('1')
        self.assertEqual(D(normalize_input(self.app.conv_input.get())),D('.3048'))
    def test_unit_temperature(self):
        self.app.switch_aux('Unit conversion');self.app.conv_category.set('Temperature');self.app.conversion_category_changed()
        self.app.conv_input.set('100');self.assertEqual(D(self.app.conv_output.get()),212)
    def test_date_difference(self):
        self.app.switch_aux('Date calculation');self.app.date_from.set('2024-01-01');self.app.date_to.set('2025-01-01')
        self.app.calculate_dates();self.assertIn('366 Tage',self.app.date_result.get())
    def test_date_add(self):
        self.app.switch_aux('Date calculation');self.app.date_operation.set('Add / subtract');self.app.rebuild_dates()
        self.app.date_from.set('2024-01-31');self.app.date_months.set('1');self.app.calculate_dates()
        self.assertIn('2024-02-29',self.app.date_result.get())
    def test_worksheets_all_targets(self):
        for name,fields in WORKSHEETS.items():
            self.app.switch_aux(name)
            for key,label in fields.items():
                self.app.worksheet_target.set(label);self.app.rebuild_worksheet();self.root.update()
                self.assertFalse(self.app.panel_error.get(),(name,key,self.app.panel_error.get()))
    def test_switching_all_modes_aux(self):
        for mode in ('Standard','Scientific','Programmer','Statistics'):
            self.app.switch_mode(mode)
            for aux in ('Unit conversion','Date calculation',*WORKSHEETS,'Basic'):
                self.app.switch_aux(aux);self.root.update()
                self.assertGreater(self.root.winfo_width(),100)
    def test_invalid_conversion(self):
        self.app.switch_aux('Unit conversion');self.app.conv_input.set('not a number')
        self.assertTrue(self.app.panel_error.get());self.assertEqual(self.app.conv_output.get(),'')
    def test_error_recovery_buttons(self):
        for key in ('digit_8','/','digit_0','equals'):self.click(key)
        self.assertEqual(self.app.calc.error,'Cannot divide by zero')
        self.click('digit_4');self.assertEqual(self.app.calc.value,4);self.assertFalse(self.app.calc.error)
    def test_scale(self):
        self.app.change_scale(1.5);self.root.update();self.assertGreater(self.root.winfo_width(),300)
        self.app.switch_mode('Programmer');self.root.update();self.assertGreater(self.root.winfo_width(),600)
    def test_clipboard(self):
        self.app.calc.paste('123.456');self.app.copy();self.assertEqual(self.root.clipboard_get(),'123,456')
        self.root.clipboard_clear();self.root.clipboard_append('42');self.app.paste();self.assertEqual(self.app.calc.value,42)
    def test_enter_after_click(self):
        # Enter calculates instead of reinvoking the focused digit button.
        for key in ('digit_2','+','digit_3'):self.click(key)
        self.app.buttons['digit_3'].focus_set();self.root.update()
        self.app.buttons['digit_3'].event_generate('<KeyPress-Return>');self.root.update()
        self.assertEqual(self.app.calc.value,5)
    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            self.app.config_path=Path(directory)/'state.json';self.app.fresh=False
            self.app.switch_mode('Scientific');self.app.calc.paste('42');self.app.calc.memory_action('MS')
            self.app.calc.equals();self.app.calc.samples=[D('1.5'),D('2.5')];self.app.save_state()
            data=json.loads(self.app.config_path.read_text());self.assertEqual(data['memory'],'42')
            self.app.calc.clear();self.app.calc.history=[];self.app.calc.samples=[];self.app.load_state()
            self.assertEqual(self.app.calc.memory,42);self.assertEqual(len(self.app.calc.history),1)
            self.assertEqual(self.app.calc.samples,[D('1.5'),D('2.5')])
            self.assertEqual(self.app.config_path.stat().st_mode & 0o777,0o600)
    def test_corrupt_state(self):
        with tempfile.TemporaryDirectory() as directory:
            self.app.config_path=Path(directory)/'state.json';self.app.config_path.write_text('not json');self.app.load_state()
            self.app.config_path.write_text('{"samples":null}');self.app.load_state()
    def test_fresh_no_state_write(self):
        with tempfile.TemporaryDirectory() as directory:
            self.app.config_path=Path(directory)/'state.json';self.app.save_state();self.assertFalse(self.app.config_path.exists())
