"""UI integration checks; no paid model requests."""
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class AppTests(unittest.TestCase):
    def start(self):
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        self.assertFalse(app.exception)
        app.checkbox[0].set_value(True).run()
        return app

    def test_offline_and_stale_results(self):
        app = self.start()
        app.button[0].click().run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, '6,150.00')
        self.assertEqual(len(app.metric), 3)
        app.text_input[0].set_value('新的分析问题').run()
        self.assertEqual(len(app.metric), 0)

    def test_invalid_fields_clear_results(self):
        app = self.start()
        app.button[0].click().run(timeout=20)
        app.selectbox[1].set_value('date').run()
        app.button[0].click().run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.metric), 0)
        self.assertFalse(app.exception)

    def test_online_without_config_never_calls_model(self):
        import os
        app = self.start()
        with patch.dict(os.environ, {'ONLINE_PASSWORD_HASH': ''}):
            app.checkbox[0].set_value(False).run()
            with patch('orchestration.run_analysis') as call:
                app.button[0].click().run()
                call.assert_not_called()
        self.assertTrue(app.error)
        self.assertFalse(app.exception)

    def test_blank_question(self):
        app = self.start()
        app.text_input[0].set_value('   ').run()
        with patch('orchestration.run_analysis') as call:
            app.button[0].click().run()
            call.assert_not_called()
        self.assertTrue(app.error)

    def test_unexpected_failure_sanitized(self):
        app = self.start()
        with patch('orchestration.run_analysis', side_effect=RuntimeError('secret-provider-detail')):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn('secret-provider-detail', app.error[0].value)
        self.assertEqual(len(app.metric), 0)


if __name__ == '__main__':
    unittest.main()
