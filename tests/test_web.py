import io
import sys
import os
import tempfile
import unittest
from contextlib import contextmanager
from unittest import mock

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

    def tearDown(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def login(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True

    @contextmanager
    def temp_galleries(self):
        # Point the app at an empty galleries dir, restoring the real one afterwards
        app_state = web.app_state
        original = (app_state.galleries_dir, app_state.current_folder, app_state.web_action)
        with tempfile.TemporaryDirectory() as tmp:
            app_state.galleries_dir = tmp
            app_state.refresh_folders()
            try:
                yield tmp
            finally:
                app_state.galleries_dir, app_state.current_folder, app_state.web_action = original
                app_state.refresh_folders()
                app_state.refresh_images()

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
        
    def test_settings_rejects_invalid_values(self):
        self.login()
        app_state = web.app_state
        before = (app_state.display_duration, app_state.transition_type, app_state.random_order)

        for data in [
            {'duration': 'abc', 'transition': 'cut'},
            {'duration': '7', 'transition': 'cut'},
            {'duration': '10', 'transition': 'spin'},
        ]:
            resp = self.client.post('/api/settings', data=dict(data, random='true'))
            self.assertEqual(resp.status_code, 400, data)

        self.assertEqual((app_state.display_duration, app_state.transition_type, app_state.random_order), before)

    def test_settings_saves_valid_values(self):
        self.login()
        app_state = web.app_state
        before = (app_state.display_duration, app_state.transition_type)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(state, 'settings_path', os.path.join(tmp, 'settings.json')):
            try:
                resp = self.client.post('/api/settings', data={'duration': '60', 'transition': 'fade'})
                self.assertEqual(resp.status_code, 200)
                self.assertEqual((app_state.display_duration, app_state.transition_type), (60, 'fade'))
            finally:
                app_state.display_duration, app_state.transition_type = before

    def test_tailscale_widget_renders(self):
        with self.client.session_transaction() as sess:
            sess['authenticated'] = True
            
        resp = self.client.get('/ui/tailscale')
        self.assertEqual(resp.status_code, 200)
        # It should either say Connected, Needs Login, or Not Installed
        self.assertTrue(b'Tailscale Connected' in resp.data or b'Needs Login' in resp.data or b'Not Installed' in resp.data)

    def test_upload_saves_multiple_files(self):
        self.login()
        with self.temp_galleries() as tmp:
            resp = self.client.post('/api/upload', data={
                'folder': 'images',
                'file': [(io.BytesIO(b'one'), 'one.jpg'), (io.BytesIO(b'two'), 'two.jpg')],
            }, content_type='multipart/form-data')

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(sorted(os.listdir(os.path.join(tmp, 'images'))), ['one.jpg', 'two.jpg'])

    def test_upload_keeps_extension_and_never_overwrites(self):
        self.login()
        with self.temp_galleries() as tmp:
            for _ in range(2):
                self.client.post('/api/upload', data={
                    'folder': 'images',
                    'file': [
                        (io.BytesIO(b'a'), '写真.JPG'),
                        (io.BytesIO(b'b'), 'image.jpg'),
                        (io.BytesIO(b'c'), 'notes.txt'),
                    ],
                }, content_type='multipart/form-data')

            self.assertEqual(sorted(os.listdir(os.path.join(tmp, 'images'))),
                             ['image.jpg', 'image_1.jpg', 'photo.jpg', 'photo_1.jpg'])

    def test_gallery_with_special_characters_loads(self):
        self.login()
        with self.temp_galleries() as tmp:
            os.makedirs(os.path.join(tmp, 'Mum & Dad #1'))
            open(os.path.join(tmp, 'Mum & Dad #1', 'a.jpg'), 'wb').close()
            web.app_state.refresh_folders()

            gallery = self.client.get('/ui/gallery').get_data(as_text=True)
            self.assertIn('<option value="Mum &amp; Dad #1"', gallery)

            grid = self.client.get('/ui/gallery_grid', query_string={'folder': 'Mum & Dad #1'})
            self.assertIn(b'Photos (1)', grid.data)
            self.assertIn(b'/api/image/Mum%20&amp;%20Dad%20%231/a.jpg', grid.data)
            self.assertEqual(self.client.get('/api/image/Mum%20&%20Dad%20%231/a.jpg').status_code, 200)

    def test_new_gallery_is_selected_after_creation(self):
        self.login()
        with self.temp_galleries():
            html = self.client.post('/api/create_folder', data={'new_folder': 'holiday'}).get_data(as_text=True)

            self.assertIn('<option value="holiday" selected>', html)
            self.assertIn('id="upload-folder-input" value="holiday"', html)
            self.assertEqual(web.app_state.current_folder, 'images')

    def test_filenames_are_escaped_in_grid(self):
        self.login()
        with self.temp_galleries() as tmp:
            open(os.path.join(tmp, 'images', "Dad's <b>60th.jpg"), 'wb').close()

            grid = self.client.get('/ui/gallery_grid?folder=images').get_data(as_text=True)
            self.assertNotIn('<b>60th', grid)
            self.assertIn('onclick="openPreview(this.dataset.src)"', grid)

if __name__ == '__main__':
    unittest.main()
