import sys
import os
import json
import tempfile
import unittest
from unittest import mock

# Add src to python path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import state

class SaveSettingsTestCase(unittest.TestCase):
    def setUp(self):
        self.app_state = state.AppState()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "settings.json")
        patcher = mock.patch.object(state, "settings_path", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_writes_settings_and_leaves_no_temp_file(self):
        self.app_state.display_duration = 60
        self.app_state.save_settings()

        with open(self.path) as f:
            self.assertEqual(json.load(f)["duration"], 60)
        self.assertEqual(os.listdir(os.path.dirname(self.path)), ["settings.json"])

    def test_failed_save_keeps_previous_settings(self):
        self.app_state.display_duration = 30
        self.app_state.save_settings()

        def partial_write(data, f):
            f.write('{"duration": ')
            raise OSError("power cut")

        self.app_state.display_duration = 60
        with mock.patch.object(state.json, "dump", side_effect=partial_write):
            with self.assertRaises(OSError):
                self.app_state.save_settings()

        with open(self.path) as f:
            self.assertEqual(json.load(f)["duration"], 30)

    def test_invalid_saved_values_fall_back_to_defaults(self):
        with open(self.path, "w") as f:
            json.dump({"duration": 7, "transition": "spin", "folder": "images"}, f)

        self.app_state.load_settings()

        self.assertEqual(self.app_state.display_duration, 10)
        self.assertEqual(self.app_state.transition_type, "cut")

class SecretKeyTestCase(unittest.TestCase):
    def test_key_is_created_once_and_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "secret_key")
            with mock.patch.object(state, "secret_key_path", path):
                key = state.load_secret_key()
                self.assertEqual(len(key), 32)
                self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
                self.assertEqual(state.load_secret_key(), key)

if __name__ == '__main__':
    unittest.main()
