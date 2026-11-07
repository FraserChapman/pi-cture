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

if __name__ == '__main__':
    unittest.main()
