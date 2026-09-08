import sys
import os
import unittest

# Add src to python path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

import web
import state

class WebUITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize a mock app state
        web.app_state = state.AppState()
        web.flask_app.testing = True
        cls.client = web.flask_app.test_client()

    def test_login_page_loads(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'pi&middot;cture - Login', resp.data)

    def test_protected_routes_redirect(self):
        # Without session, should redirect to login
        resp = self.client.get('/ui/settings')
        self.assertEqual(resp.status_code, 302)
        self.assertIn(b'/login', resp.data)

    def test_settings_renders_when_authenticated(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
        
        resp = self.client.get('/ui/settings')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Save Settings', resp.data)
        
    def test_tailscale_widget_renders(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
            
        resp = self.client.get('/ui/tailscale')
        self.assertEqual(resp.status_code, 200)
        # It should either say Connected, Needs Login, or Not Installed
        self.assertTrue(b'Tailscale Connected' in resp.data or b'Needs Login' in resp.data or b'Not Installed' in resp.data)

if __name__ == '__main__':
    unittest.main()
