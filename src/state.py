from werkzeug.security import generate_password_hash
import os
import json
import time
import random

script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)
settings_path = os.path.join(base_dir, "settings.json")
galleries_dir = os.path.join(base_dir, "galleries")

class AppState:
    def __init__(self):
        self.display_duration = 10
        self.random_order = False
        self.current_folder = "images"
        self.transition_type = "cut"
        self.web_password_hash = generate_password_hash("admin")
        
        self.available_folders = []
        self.images = []
        self.current_index = 0
        self.last_change_time = time.time()
        self.mode = "SLIDESHOW" # "SLIDESHOW" or "MENU"
        
        self.web_action = None
        self.web_settings_updated = False
        self.galleries_dir = galleries_dir
        
        self.load_settings()
        self.refresh_folders()
        self.refresh_images()
        
    def load_settings(self):
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    data = json.load(f)
                    self.display_duration = data.get("duration", 10)
                    self.random_order = data.get("random", False)
                    self.current_folder = data.get("folder", "images")
                    self.transition_type = data.get("transition", "cut")
                    loaded_pwd = data.get("web_password")
                    if loaded_pwd:
                        if loaded_pwd.startswith("scrypt:") or loaded_pwd.startswith("pbkdf2:"):
                            self.web_password_hash = loaded_pwd
                        else:
                            self.web_password_hash = generate_password_hash(loaded_pwd)
                    else:
                        self.web_password_hash = generate_password_hash("admin")
            except:
                pass

    def save_settings(self):
        # Write to a temp file and swap it in, so a power cut mid-save
        # can't leave a truncated settings file (which would reset the password)
        tmp_path = settings_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump({
                "duration": self.display_duration,
                "random": self.random_order,
                "folder": self.current_folder,
                "transition": self.transition_type,
                "web_password": self.web_password_hash
            }, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, settings_path)
            
    def refresh_folders(self):
        valid_folders = []
        for d in os.listdir(self.galleries_dir):
            full_path = os.path.join(self.galleries_dir, d)
            if os.path.isdir(full_path) and d != '__pycache__':
                # ignore hidden
                if not d.startswith('.'):
                    valid_folders.append(d)

        if not valid_folders:
            valid_folders = ["images"]
            
        images_dir = os.path.join(self.galleries_dir, "images")
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            if "images" not in valid_folders:
                valid_folders.append("images")
                
        self.available_folders = sorted(list(set(valid_folders)))
        if self.current_folder not in self.available_folders:
            self.current_folder = self.available_folders[0]

    def refresh_images(self):
        d = os.path.join(self.galleries_dir, self.current_folder)
        if not os.path.exists(d):
            self.images = []
        else:
            self.images = sorted([os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            
    def get_next_index(self):
        if not self.images: return 0
        if self.random_order:
            return random.randint(0, len(self.images) - 1)
        return (self.current_index + 1) % len(self.images)

    def get_prev_index(self):
        if not self.images: return 0
        if self.random_order:
            return random.randint(0, len(self.images) - 1)
        return (self.current_index - 1) % len(self.images)
