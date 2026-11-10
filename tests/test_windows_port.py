"""Windows boundary checks, plus GUI behavior shared with the Windows port.

Mocked Win32 API/path tests run on Linux too; they are not native Windows tests.
"""
import ast
import ctypes
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

from classiccalc import __version__
from classiccalc import platform_support as ps
from classiccalc.launcher import gui_main
from classiccalc.mathlib import D

ROOT = Path(__file__).resolve().parents[1]


class PlatformTests(unittest.TestCase):
    def test_windows_appdata(self):
        self.assertEqual(ps.settings_path(platform='win32', environ={'APPDATA': '/users/Sam/Roaming'}, home=Path('/home/test')),
                         Path('/users/Sam/Roaming/ClassicCalc/state.json'))

    def test_windows_home_fallback(self):
        self.assertEqual(ps.settings_path(platform='win32', environ={}, home=Path('/users/Sam')),
                         Path('/users/Sam/AppData/Roaming/ClassicCalc/state.json'))

    def test_windows_empty_appdata(self):
        self.assertEqual(ps.settings_path(platform='win32', environ={'APPDATA': ''}, home=Path('/users/Sam')),
                         Path('/users/Sam/AppData/Roaming/ClassicCalc/state.json'))

    def test_windows_ignores_xdg(self):
        path = ps.settings_path(platform='win32', environ={'APPDATA': '/data', 'XDG_CONFIG_HOME': '/wrong'}, home=Path('/h'))
        self.assertEqual(path, Path('/data/ClassicCalc/state.json'))

    def test_non_ascii_user_profile(self):
        path = ps.settings_path(platform='win32', environ={'APPDATA': '/users/Jörg Müller/Anwendungsdaten'}, home=Path('/h'))
        self.assertEqual(path.parent, Path('/users/Jörg Müller/Anwendungsdaten/ClassicCalc'))

    def test_linux_retains_xdg(self):
        self.assertEqual(ps.settings_path(platform='linux', environ={'XDG_CONFIG_HOME': '/settings'}, home=Path('/h')),
                         Path('/settings/classic-calc/state.json'))

    def test_linux_default(self):
        self.assertEqual(ps.settings_path(platform='linux', environ={}, home=Path('/h')),
                         Path('/h/.config/classic-calc/state.json'))

    def test_path_lookup_has_no_side_effects(self):
        with tempfile.TemporaryDirectory() as folder:
            p = ps.settings_path(platform='win32', environ={'APPDATA': folder}, home=Path(folder))
            self.assertFalse(p.parent.exists())

    def test_dpi_scale(self):
        for dpi, expected in ((96, 1), (120, 1.25), (144, 1.5), (192, 2), (288, 3), (384, 3), (48, .75)):
            self.assertEqual(ps.scale_from_dpi(dpi), expected)

    def test_invalid_dpi_is_safe(self):
        for value in (0, -1, float('nan'), float('inf')):
            self.assertEqual(ps.scale_from_dpi(value), 1)

    def test_linux_dpi_does_not_load_win32(self):
        with patch.object(ps.sys, 'platform', 'linux'), patch.object(ctypes, 'WinDLL', create=True) as dll:
            ps.prepare_windows_process()
            self.assertEqual(ps.initial_scale(None), 1)
            dll.assert_not_called()

    def test_windows_process_context_and_app_id(self):
        shell, user = MagicMock(), MagicMock()
        user.SetProcessDpiAwarenessContext.return_value = 1
        with patch.object(ps.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', create=True, side_effect=[shell, user]):
            ps.prepare_windows_process()
        shell.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with(ps.APP_ID)
        self.assertEqual(user.SetProcessDpiAwarenessContext.call_args.args[0].value, ctypes.c_void_p(-2).value)

    def test_windows_dpi_already_set_by_manifest(self):
        shell, user = MagicMock(), MagicMock()
        user.SetProcessDpiAwarenessContext.return_value = 0
        with patch.object(ps.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', create=True, side_effect=[shell, user]) as dll, patch.object(ctypes, 'get_last_error', create=True, return_value=5):
            ps.prepare_windows_process()
            self.assertEqual(dll.call_count, 2)

    def test_missing_windows_apis_are_safe(self):
        with patch.object(ps.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', create=True, side_effect=OSError('missing API')):
            ps.prepare_windows_process()

    def test_dpi_system_query(self):
        user = MagicMock()
        user.GetDpiForSystem.return_value = 144
        with patch.object(ps.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', create=True, return_value=user):
            self.assertEqual(ps.initial_scale(None), 1.5)

    def test_dpi_tk_fallback(self):
        root = MagicMock()
        root.winfo_fpixels.return_value = 192
        with patch.object(ps.sys, 'platform', 'win32'), patch.object(ctypes, 'WinDLL', create=True, side_effect=AttributeError):
            self.assertEqual(ps.initial_scale(root), 2)

    def test_platform_specific_tk_hint(self):
        with patch.object(ps.sys, 'platform', 'win32'):
            self.assertIn('tcl/tk', ps.tkinter_install_hint())
            self.assertNotIn('sudo', ps.tkinter_install_hint())
        with patch.object(ps.sys, 'platform', 'linux'):
            self.assertIn('python3-tk', ps.tkinter_install_hint())

    def test_manifest_has_windows10_and_no_admin_request(self):
        tree = ET.parse(ROOT/'packaging/windows/app.manifest')
        elements = {el.tag.rsplit('}',1)[-1]: el for el in tree.iter()}
        self.assertEqual(elements['requestedExecutionLevel'].get('level'), 'asInvoker')
        self.assertEqual(elements['dpiAwareness'].text, 'system')
        self.assertEqual(elements['supportedOS'].get('Id'), '{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}')
        self.assertEqual(elements['assemblyIdentity'].get('version'), __version__ + '.0')

    def test_windows_scripts_have_crlf(self):
        for path in list(ROOT.glob('*.cmd')) + [ROOT/'tools/find-python.cmd']:
            data = path.read_bytes()
            self.assertIn(b'\r\n', data)
            self.assertNotIn(b'\n', data.replace(b'\r\n', b''))

    def test_readme_gallery_immediately_after_title(self):
        readme = (ROOT/'README.md').read_text(encoding='utf-8')
        self.assertTrue(readme.splitlines()[2].startswith('| Rechnermodi'))
        pictures = re.findall(r'!\[[^\]]*\]\((screenshots/[^)]+)\)', readme)
        self.assertGreaterEqual(len(pictures), 10)
        self.assertEqual(len(pictures), len(set(pictures)))
        for filename in pictures:
            self.assertTrue((ROOT/filename).is_file(), filename)

    def test_entry_points_compile(self):
        for path in [ROOT/'app.py', ROOT/'app.pyw', ROOT/'tools/build_windows.py', ROOT/'tools/start_windows.py']:
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))

    def test_version_resource_generation(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('build_windows', ROOT/'tools/build_windows.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'meta/version_info.txt'
            module.write_version_resource(path)
            data = path.read_text(encoding='utf-8')
            ast.parse(data)
            self.assertIn(__version__, data)
            self.assertIn('040704B0', data)


class WindowlessLauncherTests(unittest.TestCase):
    def test_success_with_normal_streams(self):
        with patch('classiccalc.__main__.main', return_value=0), patch('classiccalc.launcher._error_dialog') as dialog:
            self.assertEqual(gui_main(), 0)
            dialog.assert_not_called()

    def test_absent_streams_are_logged_and_restored(self):
        with tempfile.TemporaryDirectory() as folder:
            logfile = Path(folder)/'settings/error.log'
            def run():
                print('Prüfung: äöü', file=sys.stderr)
                return 0
            with patch('classiccalc.launcher.log_path', return_value=logfile), patch('classiccalc.__main__.main', side_effect=run), patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
                self.assertEqual(gui_main(), 0)
                self.assertIsNone(sys.stdout)
                self.assertIsNone(sys.stderr)
            self.assertIn('Prüfung: äöü', logfile.read_text(encoding='utf-8'))

    def test_startup_exception_shows_error(self):
        with patch('classiccalc.__main__.main', side_effect=RuntimeError('test startup failure')), patch('classiccalc.launcher._error_dialog') as dialog, patch.object(sys, 'stderr', io.StringIO()):
            self.assertEqual(gui_main(), 1)
            dialog.assert_called_once()

    def test_nonzero_return_shows_error(self):
        with patch('classiccalc.__main__.main', return_value=1), patch('classiccalc.launcher._error_dialog') as dialog:
            self.assertEqual(gui_main(), 1)
            dialog.assert_called_once()

    def test_readonly_log_location_still_starts(self):
        with patch('classiccalc.launcher.log_path', side_effect=PermissionError), patch('classiccalc.__main__.main', return_value=0), patch.object(sys, 'stdout', None), patch.object(sys, 'stderr', None):
            self.assertEqual(gui_main(), 0)


@unittest.skipUnless(sys.platform == 'win32' or bool(os.environ.get('DISPLAY')), 'GUI tests need a desktop')
class WindowsPortGuiTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from classiccalc.ui import CalculatorApp
        self.root = tk.Tk()
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args)
        self.app = CalculatorApp(self.root, fresh=True)
        self.root.update()

    def tearDown(self):
        self.root.destroy()
        self.assertFalse(self.errors)

    def key(self, char, key, state=0):
        event = SimpleNamespace(widget=self.app.display_canvas, char=char, keysym=key, state=state)
        return self.app.key(event)

    def test_windows_app_uses_appdata(self):
        from classiccalc.ui import CalculatorApp
        with tempfile.TemporaryDirectory() as folder, patch.object(ps.sys, 'platform', 'win32'), patch.dict(os.environ, {'APPDATA': folder}):
            other = CalculatorApp(self.root, fresh=True)
            self.root.update()
            self.assertEqual(other.config_path, Path(folder)/'ClassicCalc/state.json')

    def test_windows_altgr_square_root(self):
        self.app.calc.paste('9')
        with patch('classiccalc.ui.sys.platform', 'win32'):
            self.assertEqual(self.key('@', 'at', 0x20004), 'break')
        self.assertEqual(self.app.calc.value, 3)

    def test_windows_altgr_bitwise_or(self):
        self.app.switch_mode('Programmer')
        self.app.calc.paste('1')
        with patch('classiccalc.ui.sys.platform', 'win32'):
            self.key('|', 'bar', 0x20004)
        self.app.calc.input_digit('2')
        self.app.calc.equals()
        self.assertEqual(self.app.calc.value, 3)

    def test_windows_altgr_bitwise_not(self):
        self.app.switch_mode('Programmer')
        self.app.calc.paste('0')
        with patch('classiccalc.ui.sys.platform', 'win32'):
            self.key('~', 'asciitilde', 0x0C)
        self.assertEqual(self.app.calc.value, -1)

    def test_windows_control_keys_not_treated_as_numbers(self):
        with patch('classiccalc.ui.sys.platform', 'win32'):
            self.assertIsNone(self.key('7', '7', 0x4))
            self.assertIsNone(self.key('7', '7', 0x20000))
        self.assertEqual(self.app.calc.value, 0)

    def test_german_keypad_separator(self):
        self.key('1', 'KP_1')
        self.key(',', 'KP_Separator')
        self.key('5', 'KP_5')
        self.assertEqual(self.app.calc.value, D('1.5'))

    def test_decimal_point_key_also_works(self):
        self.key('1', '1')
        self.key('.', 'period')
        self.key('5', '5')
        self.assertEqual(self.app.calc.value, D('1.5'))

    def test_state_roundtrip_in_unicode_windows_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            self.app.config_path = Path(folder)/'Jörg Müller/AppData/Roaming/ClassicCalc/state.json'
            self.app.fresh = False
            self.app.calc.paste('1.25')
            self.app.calc.equals()
            self.app.save_state()
            data = json.loads(self.app.config_path.read_text(encoding='utf-8'))
            self.assertEqual(data['number_format'], 'canonical')
            self.assertEqual(data['history'][-1]['value'], '1.25')
            self.assertEqual(list(self.app.config_path.parent.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
