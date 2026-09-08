import os
import json
import shutil
import threading
from flask import Flask, request, redirect, url_for, render_template_string, send_file, make_response, session
import werkzeug.utils
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

flask_app = Flask(__name__)
flask_app.secret_key = os.urandom(24)

LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>pi&middot;cture - Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/static/uikit.min.css" />
    <script src="/static/uikit.min.js"></script>
    <script src="/static/uikit-icons.min.js"></script>
    <style>html { scrollbar-gutter: stable; }
        body { background: #f8f9fa; }</style>
</head>
<body class="uk-flex uk-flex-middle uk-flex-center" style="height: 100vh;">
    <div class="uk-card uk-card-default uk-card-body" style="width: 350px;">
        <h3 class="uk-card-title uk-text-center"><span>pi<span style="color: red;">&middot;</span>cture</span></h3>
        {% if error %}
        <div class="uk-alert-danger" uk-alert><p>{{ error }}</p></div>
        {% endif %}
        <form method="POST">
            <div class="uk-margin">
                <div class="uk-inline uk-width-1-1">
                    <span class="uk-form-icon" uk-icon="icon: lock"></span>
                    <input class="uk-input" type="password" name="password" placeholder="Password" required autofocus autocomplete="current-password">
                </div>
            </div>
            <div class="uk-margin">
                <button class="uk-button uk-button-primary uk-width-1-1" type="submit">Log In</button>
            </div>
        </form>
    </div>
</body>
</html>"""

@flask_app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if check_password_hash(app_state.web_password_hash, request.form.get('password')):
            session['authenticated'] = True
            return redirect(url_for('index'))
        else:
            error = "Invalid password."
    return render_template_string(LOGIN_HTML, error=error)

@flask_app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

app_state = None

MAIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>pi&middot;cture</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/static/uikit.min.css" />
    <script src="/static/uikit.min.js"></script>
    <script src="/static/uikit-icons.min.js"></script>
    <script src="/static/htmx.min.js"></script>
    <style>
        html { scrollbar-gutter: stable; }
        body { background: #f8f9fa; }
        .uk-navbar-container { background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        :root { --thumb-size: 200px; }
        .custom-gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(var(--thumb-size), 1fr));
            gap: 15px;
        }
    </style>
</head>
<body>
    <nav class="uk-navbar-container" uk-navbar>
        <div class="uk-navbar-center">
            <span class="uk-navbar-item uk-logo"><span>pi<span style="color: red;">&middot;</span>cture</span></span>
        </div>
    </nav>
    <div class="uk-container uk-margin-top uk-margin-bottom">
        <div class="uk-card uk-card-default uk-card-body">
            <ul uk-tab>
                <li><a href="#">Gallery</a></li>
                <li><a href="#">Controls</a></li>
                <li><a href="#">Settings</a></li>
            </ul>
            <ul class="uk-switcher uk-margin">
                <li id="tab-gallery" hx-get="/ui/gallery" hx-trigger="load"></li>
                <li id="tab-controls" hx-get="/ui/controls" hx-trigger="load"></li>
                <li id="tab-settings" hx-get="/ui/settings" hx-trigger="load, foldersChanged from:body"></li>
            </ul>
        </div>
    </div>
    <script>
        document.body.addEventListener("htmx:confirm", function(e) {
            if (e.target.hasAttribute("hx-confirm")) {
                e.preventDefault();
                UIkit.modal.confirm(e.target.getAttribute("hx-confirm")).then(function() {
                    e.detail.issueRequest(true);
                }, function() {
                    // cancelled
                });
            }
        });

        document.body.addEventListener("htmx:afterRequest", function(evt) {
            var msg = evt.detail.xhr.getResponseHeader("HX-Trigger");
            if (msg) {
                try {
                    var triggers = JSON.parse(msg);
                    if (triggers.notify) {
                        UIkit.notification({message: triggers.notify, status: 'success', pos: 'top-center', timeout: 3000});
                    }
                } catch(e) {}
            }
        });
    </script>
</body>
</html>
"""

@flask_app.route('/')
@login_required
def index():
    return MAIN_HTML


def get_tailscale_status():
    try:
        import subprocess, json
        result = subprocess.run(['tailscale', 'status', '--json'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            backend_state = data.get("BackendState", "Unknown")
            if backend_state == "Running":
                self_info = data.get("Self", {})
                tailnet = data.get("CurrentTailnet", {})
                hostname = self_info.get("HostName", "Unknown")
                ips = self_info.get("TailscaleIPs", [""])
                ip = ips[0] if ips else "Unknown"
                account = tailnet.get("Name", "Unknown")
                
                peers = []
                for peer_key, peer_data in data.get("Peer", {}).items():
                    peers.append({
                        "hostname": peer_data.get("HostName", "Unknown"),
                        "os": peer_data.get("OS", ""),
                        "online": peer_data.get("Online", False)
                    })
                
                user_id = str(self_info.get("UserID", ""))
                user_info = data.get("User", {}).get(user_id, {})
                display_name = user_info.get("DisplayName", account)
                profile_pic = user_info.get("ProfilePicURL", "")
                
                return {
                    "status": "connected",
                    "hostname": hostname,
                    "ip": ip,
                    "account": account,
                    "display_name": display_name,
                    "profile_pic": profile_pic,
                    "peers": peers
                }
            elif backend_state == "NeedsLogin":
                return {"status": "needs_login"}
            else:
                return {"status": "error", "message": backend_state}
        else:
            return {"status": "not_installed"}
    except Exception as e:
        return {"status": "not_installed"}

@flask_app.route('/ui/tailscale')
@login_required
def ui_tailscale():
    ts = get_tailscale_status()
    if ts["status"] == "connected":
        peers_html = '<h5 class="uk-margin-top uk-margin-small-bottom">Other Network Devices:</h5><ul class="uk-list uk-list-divider uk-text-small uk-margin-remove-bottom">'
        if not ts.get('peers'):
            peers_html += '<li>No other devices found.</li>'
        else:
            for p in ts['peers']:
                status_icon = '<span uk-icon="icon: check; ratio: 0.8" style="color: green;" uk-tooltip="Online"></span>' if p['online'] else '<span uk-icon="icon: close; ratio: 0.8" style="color: gray;" uk-tooltip="Offline"></span>'
                os_name = p['os'].lower()
                os_icon = "desktop"
                if 'android' in os_name: os_icon = 'android-robot'
                elif 'ios' in os_name or 'mac' in os_name or 'darwin' in os_name: os_icon = 'apple'
                elif 'linux' in os_name: os_icon = 'server'
                
                peers_html += f"<li>{status_icon} <span uk-icon='icon: {os_icon}; ratio: 0.8' class='uk-margin-small-right'></span> <strong>{p['hostname']}</strong> <span class='uk-text-muted uk-text-small'>({p['os']})</span></li>"
        peers_html += '</ul>'
        
        profile_img = f'<img class="uk-border-circle uk-margin-small-right" width="40" height="40" src="{ts["profile_pic"]}">' if ts.get("profile_pic") else '<span uk-icon="icon: user; ratio: 1.5" class="uk-margin-small-right"></span>'
        
        return f'''
        <div uk-alert>
            <div class="uk-flex uk-flex-middle">
                {profile_img}
                <div>
                    <p class="uk-margin-remove"><strong><span uk-icon="check"></span> Tailscale Connected</strong></p>
                    <p class="uk-text-small uk-text-muted uk-margin-remove">{ts.get('display_name')} ({ts['account']})</p>
                </div>
            </div>
            
            <hr class="uk-divider-small uk-margin-small">
            <p class="uk-margin-small-bottom">Secure global access URL:</p>
            <p class="uk-margin-remove-top"><a href="http://{ts['hostname']}:5000" target="_blank"><strong>http://{ts['hostname']}:5000</strong></a></p>
            
            {peers_html}
        </div>'''
    elif ts["status"] == "needs_login":
        return '''
        <div class="uk-alert-warning" uk-alert>
            <p><strong><span uk-icon="warning"></span> Needs Login</strong></p>
            <p>Tailscale is installed but not authenticated. Run <code>sudo tailscale up</code> on the Pi terminal to log in.</p>
        </div>'''
    else:
        return '''
        <div class="uk-alert-danger" uk-alert>
            <p><strong><span uk-icon="close"></span> Not Installed / Offline</strong></p>
            <p>Tailscale is not running on this device. Install it to enable secure global remote access.</p>
        </div>'''

@flask_app.route('/ui/settings')
@login_required
def ui_settings():

    html = f"""
    <form hx-post="/api/settings" hx-swap="none" class="uk-form-stacked">
        <div class="uk-grid-small uk-child-width-1-2@s" uk-grid>
            <div>
                <label class="uk-form-label">Duration (seconds)</label>
                <div class="uk-form-controls">
                    <select class="uk-select" name="duration">
                        <option value="5" {'selected' if app_state.display_duration == 5 else ''}>5</option>
                        <option value="10" {'selected' if app_state.display_duration == 10 else ''}>10</option>
                        <option value="30" {'selected' if app_state.display_duration == 30 else ''}>30</option>
                        <option value="60" {'selected' if app_state.display_duration == 60 else ''}>60</option>
                    </select>
                </div>
            </div>
            <div>
                <label class="uk-form-label">Order</label>
                <div class="uk-form-controls">
                    <select class="uk-select" name="random">
                        <option value="false" {'selected' if not app_state.random_order else ''}>Sequential</option>
                        <option value="true" {'selected' if app_state.random_order else ''}>Random</option>
                    </select>
                </div>
            </div>
            <div>
                <label class="uk-form-label">Folder</label>
                <div class="uk-form-controls">
                    <select class="uk-select" name="folder">
                        """
    for f in app_state.available_folders:
        selected = 'selected' if f == app_state.current_folder else ''
        html += f'<option value="{f}" {selected}>{f}</option>'
        
    html += f"""
                    </select>
                </div>
            </div>
            <div>
                <label class="uk-form-label">Transition</label>
                <div class="uk-form-controls">
                    <select class="uk-select" name="transition">
                        <option value="cut" {'selected' if app_state.transition_type == 'cut' else ''}>Cut</option>
                        <option value="fade" {'selected' if app_state.transition_type == 'fade' else ''}>Fade</option>
                        <option value="slide" {'selected' if app_state.transition_type == 'slide' else ''}>Slide</option>
                    </select>
                </div>
            </div>
            <div>
                <label class="uk-form-label">Web Password</label>
                <div class="uk-form-controls">
                    <input class="uk-input" type="password" name="web_password" placeholder="Leave blank to keep current" autocomplete="new-password">
                </div>
            </div>
        </div>
        <div class="uk-margin">
            <button class="uk-button uk-button-primary" type="submit">Save Settings</button>
            <a href="/logout" class="uk-button uk-button-default uk-float-right">Log Out</a>
        </div>
    </form>
    
    <hr class="uk-divider-icon">
    <h4>Remote Access (Tailscale)</h4>
    <div hx-get="/ui/tailscale" hx-trigger="load, every 10s">
        <div class="uk-text-center uk-margin-small">
            <div uk-spinner="ratio: 1"></div> <span class="uk-text-muted uk-margin-small-left">Checking Tailscale status...</span>
        </div>
    </div>
    """
    return html

@flask_app.route('/ui/controls')
@login_required
def ui_controls():
    return """
    <div class="uk-grid-small uk-child-width-1-3@s uk-text-center" uk-grid>
        <div>
            <button class="uk-button uk-button-default uk-width-1-1" style="height: 100px;" hx-post="/api/action" hx-vals='{"action": "prev"}' hx-swap="none">
                <span uk-icon="icon: chevron-left; ratio: 2"></span><br>Previous
            </button>
        </div>
        <div>
            <button class="uk-button uk-button-default uk-width-1-1" style="height: 100px;" hx-post="/api/action" hx-vals='{"action": "reload"}' hx-swap="none">
                <span uk-icon="icon: refresh; ratio: 2"></span><br>Reload
            </button>
        </div>
        <div>
            <button class="uk-button uk-button-default uk-width-1-1" style="height: 100px;" hx-post="/api/action" hx-vals='{"action": "next"}' hx-swap="none">
                <span uk-icon="icon: chevron-right; ratio: 2"></span><br>Next
            </button>
        </div>
    </div>
    """

@flask_app.route('/ui/gallery')
@login_required
def ui_gallery(selected_folder=None):
    if selected_folder is None or selected_folder not in app_state.available_folders:
        selected_folder = app_state.current_folder
    d = os.path.join(app_state.galleries_dir, app_state.current_folder)
    count = 0
    if os.path.exists(d):
        count = len([f for f in os.listdir(d) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
        
    html = f"""
    <div class="uk-grid-small" uk-grid>
        <div class="uk-width-1-2@s">
            <h4>Gallery Controls</h4>
            <form id="gallery-controls-form" hx-get="/ui/gallery_grid" hx-target="#gallery-grid" hx-trigger="change from:select">
                <div class="uk-flex uk-flex-middle uk-margin-small-bottom">
                    <select class="uk-select uk-margin-small-right" id="folder-select" name="folder">
                        """
    for f in app_state.available_folders:
        selected = 'selected' if f == app_state.current_folder else ''
        html += f'<option value="{f}" {selected}>{f}</option>'
        
    html += f"""
                    </select>
                    <button type="button" class="uk-button uk-button-danger" onclick="deleteSelectedGallery()" uk-tooltip="Delete Gallery" uk-icon="trash"></button>
                </div>
                <div class="uk-flex uk-flex-middle">
                    <select class="uk-select uk-margin-small-right" name="per_page" style="max-width: 150px;">
                        <option value="12">12 per page</option>
                        <option value="24" selected>24 per page</option>
                        <option value="48">48 per page</option>
                        <option value="96">96 per page</option>
                    </select>
                    
                    <div class="uk-flex uk-flex-middle uk-width-expand">
                        <span uk-icon="image" class="uk-margin-small-right"></span>
                        <input type="range" class="uk-range" min="100" max="400" value="200" id="thumb-size-slider">
                    </div>
                </div>
            </form>
        </div>
        <div class="uk-width-1-2@s">
            <h4>Create New Gallery</h4>
            <form hx-post="/api/create_folder" hx-target="#tab-gallery" hx-swap="innerHTML" class="uk-flex uk-flex-middle">
                <input class="uk-input uk-margin-small-right" type="text" name="new_folder" placeholder="Gallery Name" required>
                <button class="uk-button uk-button-default" type="submit">Create</button>
            </form>
        </div>
    </div>
    
    <hr class="uk-divider-icon">
    
    <div class="uk-flex uk-flex-between uk-flex-middle uk-margin-bottom">
        <h3 class="uk-margin-remove" id="gallery-photo-count">Photos ({count})</h3>
        <form hx-post="/api/upload" hx-encoding="multipart/form-data" hx-target="#gallery-grid" hx-swap="innerHTML">
            <div uk-form-custom>
                <input type="file" name="file" accept=".jpg,.jpeg,.png" required onchange="this.closest('form').dispatchEvent(new Event('submit', {{cancelable: true}}))">
                <button class="uk-button uk-button-primary" type="button" tabindex="-1">
                    <span uk-icon="upload"></span> Upload Photo
                </button>
            </div>
            <input type="hidden" name="folder" id="upload-folder-input" value="{selected_folder}">
        </form>
    </div>
    
    <script>
        document.getElementById('folder-select').addEventListener('change', function(e) {{
            document.getElementById('upload-folder-input').value = e.target.value;
        }});
        
        document.getElementById('thumb-size-slider').addEventListener('input', function(e) {{
            document.documentElement.style.setProperty('--thumb-size', e.target.value + 'px');
        }});
        
        function deleteSelectedGallery() {{
            var folder = document.getElementById('folder-select').value;
            if (folder === 'images') {{
                UIkit.notification({{message: 'Cannot delete the default images gallery.', status: 'danger', pos: 'top-center'}});
                return;
            }}
            UIkit.modal.confirm('Are you sure you want to delete the gallery "' + folder + '" and all its photos? This cannot be undone.').then(function() {{
                htmx.ajax('DELETE', '/api/folder/' + encodeURIComponent(folder), {{target: '#tab-gallery', swap: 'innerHTML'}});
            }}, function () {{
                // cancelled
            }});
        }}
        
        function openPreview(src) {{
            document.getElementById('modal-preview-img').src = src;
            UIkit.modal(document.getElementById('modal-media-image')).show();
        }}
    </script>
    
    <div id="modal-media-image" class="uk-flex-top" uk-modal>
        <div class="uk-modal-dialog uk-width-auto uk-margin-auto-vertical">
            <button class="uk-modal-close-outside" type="button" uk-close></button>
            <img id="modal-preview-img" src="" alt="Preview" style="max-width: 90vw; max-height: 90vh; object-fit: contain; background: black;">
        </div>
    </div>

    <div id="gallery-grid" hx-get="/ui/gallery_grid?folder={selected_folder}&per_page=24" hx-trigger="load">
        <div class="uk-text-center uk-margin-large">
            <div uk-spinner="ratio: 2"></div>
        </div>
    </div>
    """
    return html

@flask_app.route('/ui/gallery_grid')
@login_required
def gallery_grid():
    folder = request.args.get('folder', app_state.current_folder)
    if folder not in app_state.available_folders:
        return f"<div class='uk-alert uk-alert-danger'>Invalid folder.</div>"
        
    try:
        per_page = int(request.args.get('per_page', 24))
    except:
        per_page = 24
        
    page = int(request.args.get('page', 1))

    d = os.path.join(app_state.galleries_dir, folder)
    if not os.path.exists(d):
        return f"<h3 class='uk-margin-remove' id='gallery-photo-count' hx-swap-oob='true'>Photos (0)</h3><div class='uk-alert uk-alert-warning'>Folder not found.</div>"

    images = sorted([f for f in os.listdir(d) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    total_images = len(images)
    
    html = f"<h3 class='uk-margin-remove' id='gallery-photo-count' hx-swap-oob='true'>Photos ({total_images})</h3>"
    
    if not images:
        return html + f"<div class='uk-alert'>No photos found in '{folder}'.</div>"

    total_pages = (total_images - 1) // per_page + 1
    if page > total_pages:
        page = total_pages
        
    start = (page - 1) * per_page
    end = start + per_page
    page_images = images[start:end]

    html += '<div class="custom-gallery-grid">'
    for img in page_images:
        html += f'''
        <div class="uk-card uk-card-default uk-card-small uk-inline" style="width: 100%;">
            <div class="uk-card-media-top" style="aspect-ratio: 4/3; background: #222; cursor: pointer;" onclick="openPreview('/api/image/{folder}/{img}')">
                <img src="/api/image/{folder}/{img}" style="width: 100%; height: 100%; object-fit: contain;" loading="lazy">
            </div>
            <div class="uk-position-top-right uk-position-small">
                <button class="uk-icon-button" style="background: rgba(255,255,255,0.8); color: red;" 
                        uk-icon="trash"
                        hx-delete="/api/image/{folder}/{img}" 
                        hx-confirm="Delete {img}?" 
                        hx-target="closest div.uk-card" 
                        hx-swap="outerHTML"
                        onclick="event.stopPropagation();"></button>
            </div>
        </div>
        '''
    html += '</div>'

    if total_pages > 1:
        html += '<nav aria-label="Pagination" class="uk-margin-large-top"><ul class="uk-pagination uk-flex-center" uk-margin>'
        
        if page > 1:
            html += f'<li><a hx-get="/ui/gallery_grid?folder={folder}&per_page={per_page}&page={page-1}" hx-target="#gallery-grid"><span uk-pagination-previous></span></a></li>'
        else:
            html += '<li class="uk-disabled"><span><span uk-pagination-previous></span></span></li>'
            
        pages = []
        if total_pages <= 7:
            pages = list(range(1, total_pages + 1))
        else:
            pages.append(1)
            if page > 4:
                pages.append("...")
                
            start_p = max(2, page - 2)
            end_p = min(total_pages - 1, page + 2)
            
            if page <= 4:
                end_p = 6
            elif page >= total_pages - 3:
                start_p = total_pages - 5
                
            for i in range(start_p, end_p + 1):
                pages.append(i)
                
            if page < total_pages - 3:
                pages.append("...")
            pages.append(total_pages)
            
        for p in pages:
            if p == "...":
                html += '<li class="uk-disabled"><span>…</span></li>'
            elif p == page:
                html += f'<li class="uk-active"><span aria-current="page">{p}</span></li>'
            else:
                html += f'<li><a hx-get="/ui/gallery_grid?folder={folder}&per_page={per_page}&page={p}" hx-target="#gallery-grid">{p}</a></li>'
                
        if page < total_pages:
            html += f'<li><a hx-get="/ui/gallery_grid?folder={folder}&per_page={per_page}&page={page+1}" hx-target="#gallery-grid"><span uk-pagination-next></span></a></li>'
        else:
            html += '<li class="uk-disabled"><span><span uk-pagination-next></span></span></li>'
            
        html += '</ul></nav>'
        
    return html

@flask_app.route('/api/settings', methods=['POST'])
@login_required
def update_settings_api():
    app_state.display_duration = int(request.form.get('duration', app_state.display_duration))
    app_state.random_order = request.form.get('random') == 'true'
    
    new_pwd = request.form.get('web_password')
    if new_pwd:
        app_state.web_password_hash = generate_password_hash(new_pwd)
    
    new_folder = request.form.get('folder', app_state.current_folder)
    app_state.transition_type = request.form.get('transition', app_state.transition_type)
    
    if new_folder != app_state.current_folder and new_folder in app_state.available_folders:
        app_state.current_folder = new_folder
        app_state.web_settings_updated = True
        
    app_state.save_settings()
    
    resp = make_response("")
    resp.headers['HX-Trigger'] = json.dumps({"notify": "Settings saved!"})
    return resp

@flask_app.route('/api/create_folder', methods=['POST'])
@login_required
def create_folder_api():
    new_folder = request.form.get('new_folder')
    if new_folder:
        if '/' not in new_folder and '\\' not in new_folder and new_folder != '..':
            target_dir = os.path.join(app_state.galleries_dir, new_folder)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            app_state.refresh_folders()
            
    resp = make_response(ui_gallery(selected_folder=new_folder))
    resp.headers['HX-Trigger'] = 'foldersChanged'
    return resp

@flask_app.route('/api/folder/<folder_name>', methods=['DELETE'])
@login_required
def delete_folder_api(folder_name):
    if folder_name == 'images':
        return "Cannot delete default gallery", 400
    if folder_name not in app_state.available_folders:
        return "Not found", 404
        
    target_dir = os.path.join(app_state.galleries_dir, folder_name)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        app_state.refresh_folders()
        if app_state.current_folder == folder_name:
            app_state.current_folder = app_state.available_folders[0]
            app_state.refresh_images()
            app_state.web_action = 'reload'
            app_state.save_settings()
            app_state.web_settings_updated = True
            
    resp = make_response(ui_gallery())
    resp.headers['HX-Trigger'] = 'foldersChanged'
    return resp

@flask_app.route('/api/action', methods=['POST'])
@login_required
def api_action():
    app_state.web_action = request.form.get('action')
    resp = make_response("")
    resp.headers['HX-Trigger'] = json.dumps({"notify": "Action sent to display"})
    return resp

@flask_app.route('/api/upload', methods=['POST'])
@login_required
def upload_file_api():
    folder = request.form.get('folder', app_state.current_folder)
    if folder not in app_state.available_folders:
        return "Invalid folder", 400
        
    if 'file' not in request.files:
        return "No file", 400
    file = request.files['file']
    if file and file.filename:
        filename = werkzeug.utils.secure_filename(file.filename)
        target_dir = os.path.join(app_state.galleries_dir, folder)
        os.makedirs(target_dir, exist_ok=True)
        file.save(os.path.join(target_dir, filename))
        
        if app_state.current_folder == folder:
            app_state.refresh_images()
            app_state.web_action = 'reload'
            
    return redirect(url_for('gallery_grid', folder=folder))

@flask_app.route('/api/image/<folder>/<filename>', methods=['GET'])
@login_required
def get_image_file(folder, filename):
    if folder not in app_state.available_folders:
        return "Not found", 404
    if '/' in filename or '\\' in filename:
        return "Invalid filename", 400
        
    path = os.path.join(app_state.galleries_dir, folder, filename)
    if os.path.exists(path):
        return send_file(path)
    return "Not found", 404

@flask_app.route('/api/image/<folder>/<filename>', methods=['DELETE'])
@login_required
def delete_image_file(folder, filename):
    if folder not in app_state.available_folders:
        return "Not found", 404
    if '/' in filename or '\\' in filename:
        return "Invalid filename", 400
        
    path = os.path.join(app_state.galleries_dir, folder, filename)
    if os.path.exists(path):
        os.remove(path)
        if app_state.current_folder == folder:
            app_state.refresh_images()
            app_state.web_action = 'reload'
        images = [f for f in os.listdir(os.path.join(app_state.galleries_dir, folder)) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        total = len(images)
        return f"<h3 class='uk-margin-remove' id='gallery-photo-count' hx-swap-oob='true'>Photos ({total})</h3>"
    return "Not found", 404

def start_web_server(state):
    global app_state
    app_state = state
    threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=int(os.environ.get("PICTURE_PORT", 5000)), debug=False, use_reloader=False), daemon=True).start()
