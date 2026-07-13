from flask import Flask, request, render_template_string, send_from_directory, jsonify, session, redirect, url_for
import os
import datetime
import hashlib
import json
import mimetypes
import base64
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.aiff import AIFF
from mutagen.apev2 import APEv2File

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-it-12345'

CONFIG_FILE = 'storage_config.json'

def load_storages():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_storages(storages):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(storages, f, ensure_ascii=False, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_audio_metadata(filepath):
    try:
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext in ['.mp3']:
            audio = MP3(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': str(audio.get('TIT2', os.path.basename(filepath))),
                'artist': str(audio.get('TPE1', 'Unknown Artist')),
                'album': str(audio.get('TALB', 'Unknown Album')),
                'year': str(audio.get('TDRC', '')),
                'genre': str(audio.get('TCON', '')),
                'track': str(audio.get('TRCK', ''))
            }
            if 'APIC:' in audio or 'APIC' in audio:
                info['has_cover'] = True
            else:
                info['has_cover'] = False
            return info
            
        elif ext in ['.flac']:
            audio = FLAC(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': str(audio.get('title', [os.path.basename(filepath)])[0]),
                'artist': str(audio.get('artist', ['Unknown Artist'])[0]),
                'album': str(audio.get('album', ['Unknown Album'])[0]),
                'year': str(audio.get('date', [''])[0]),
                'genre': str(audio.get('genre', [''])[0]),
                'track': str(audio.get('tracknumber', [''])[0]),
                'has_cover': len(audio.pictures) > 0
            }
            return info
            
        elif ext in ['.ogg', '.oga']:
            audio = OggVorbis(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': str(audio.get('title', [os.path.basename(filepath)])[0]),
                'artist': str(audio.get('artist', ['Unknown Artist'])[0]),
                'album': str(audio.get('album', ['Unknown Album'])[0]),
                'year': str(audio.get('date', [''])[0]),
                'genre': str(audio.get('genre', [''])[0]),
                'has_cover': False
            }
            return info
            
        elif ext in ['.m4a', '.mp4']:
            audio = MP4(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': str(audio.get('\xa9nam', [os.path.basename(filepath)])[0]),
                'artist': str(audio.get('\xa9ART', ['Unknown Artist'])[0]),
                'album': str(audio.get('\xa9alb', ['Unknown Album'])[0]),
                'year': str(audio.get('\xa9day', [''])[0]),
                'genre': str(audio.get('\xa9gen', [''])[0]),
                'track': str(audio.get('trkn', [['']])[0][0]),
                'has_cover': 'covr' in audio
            }
            return info
            
        elif ext in ['.wav']:
            audio = WAVE(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': os.path.basename(filepath),
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'year': '',
                'genre': '',
                'has_cover': False
            }
            return info
            
        elif ext in ['.aif', '.aiff']:
            audio = AIFF(filepath)
            info = {
                'duration': int(audio.info.length),
                'title': os.path.basename(filepath),
                'artist': 'Unknown Artist',
                'album': 'Unknown Album',
                'year': '',
                'genre': '',
                'has_cover': False
            }
            return info
            
        else:
            return {
                'duration': 0,
                'title': os.path.basename(filepath),
                'artist': 'Unknown',
                'album': 'Unknown',
                'year': '',
                'genre': '',
                'has_cover': False
            }
    except:
        return {
            'duration': 0,
            'title': os.path.basename(filepath),
            'artist': 'Unknown',
            'album': 'Unknown',
            'year': '',
            'genre': '',
            'has_cover': False
        }

def create_storage_structure(base_path):
    folders = ['media', 'media/music', 'media/video', 'media/img', 'uploads', 'uploads/download', 'other']
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except:
                pass

MAIN_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Файловое хранилище</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
            background: #000;
            min-height: 100vh;
            padding: 15px;
            color: #fff;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: #111;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            padding: 25px 20px;
        }
        h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 1px;
            color: #fff;
            margin-bottom: 5px;
        }
        .subtitle {
            color: #666;
            font-size: 13px;
            border-bottom: 1px solid #222;
            padding-bottom: 18px;
            margin-bottom: 20px;
        }
        .storage-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 15px 0;
        }
        .storage-card {
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            padding: 18px 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        .storage-card:active {
            background: #222;
            border-color: #444;
        }
        .storage-card .icon {
            font-size: 32px;
            display: block;
            margin-bottom: 8px;
            color: #888;
        }
        .storage-card .name {
            font-size: 14px;
            font-weight: 600;
            color: #fff;
            word-break: break-word;
        }
        .storage-card .path {
            color: #555;
            font-size: 11px;
            margin-top: 4px;
            word-break: break-all;
        }
        .storage-card .lock {
            font-size: 12px;
            color: #ff4444;
            display: block;
            margin-top: 6px;
        }
        .btn {
            background: #222;
            color: #fff;
            border: 1px solid #333;
            padding: 14px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
            width: 100%;
            letter-spacing: 0.5px;
            -webkit-tap-highlight-color: transparent;
        }
        .btn:active {
            background: #2a2a2a;
            border-color: #555;
        }
        .empty {
            color: #555;
            text-align: center;
            padding: 40px 20px;
            font-size: 14px;
            border: 1px dashed #222;
            border-radius: 8px;
            margin: 15px 0;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.95);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            padding: 20px;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: #111;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            padding: 25px 20px;
            max-width: 400px;
            width: 100%;
        }
        .modal-content h2 {
            font-size: 20px;
            color: #fff;
            margin-bottom: 18px;
            letter-spacing: 0.5px;
        }
        .modal-content p {
            color: #888;
            font-size: 14px;
            margin-bottom: 15px;
        }
        .modal-content input {
            width: 100%;
            padding: 12px 14px;
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            border-radius: 6px;
            color: #fff;
            font-size: 14px;
            margin: 8px 0;
            -webkit-appearance: none;
        }
        .modal-content input:focus {
            outline: none;
            border-color: #444;
        }
        .modal-content input::placeholder {
            color: #555;
        }
        .modal-content .btn {
            margin-top: 10px;
        }
        .modal-content .btn-secondary {
            background: transparent;
            border-color: #2a2a2a;
            color: #666;
            margin-top: 6px;
        }
        .modal-content .btn-secondary:active {
            background: #1a1a1a;
            border-color: #444;
        }
        .error {
            color: #ff4444;
            font-size: 13px;
            margin-top: 8px;
            display: none;
        }
        @media (max-width: 500px) {
            .storage-grid {
                grid-template-columns: 1fr 1fr;
                gap: 10px;
            }
            .container {
                padding: 18px 15px;
            }
            h1 {
                font-size: 19px;
            }
            .storage-card {
                padding: 14px 10px;
            }
            .storage-card .icon {
                font-size: 26px;
            }
            .storage-card .name {
                font-size: 13px;
            }
            .btn {
                padding: 12px 16px;
                font-size: 13px;
            }
            .modal-content {
                padding: 20px 15px;
            }
        }
        @media (max-width: 380px) {
            .storage-grid {
                grid-template-columns: 1fr;
            }
            body {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>FILE STORAGE</h1>
        <div class="subtitle">select storage to access</div>
        
        <div id="storageList">
            {% if storages %}
            <div class="storage-grid">
                {% for name, data in storages.items() %}
                <div class="storage-card" onclick="openStorage('{{ name }}')">
                    <span class="icon">[F]</span>
                    <div class="name">{{ name }}</div>
                    <div class="path">{{ data.path }}</div>
                    <span class="lock">[locked]</span>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="empty">
                [empty]<br>
                <span style="font-size: 12px; color: #444;">create storage below</span>
            </div>
            {% endif %}
        </div>
        
        <button class="btn" onclick="showCreateModal()" style="margin-top: 18px;">
            [ + ] CREATE STORAGE
        </button>
    </div>
    
    <div class="modal" id="loginModal">
        <div class="modal-content">
            <h2>[ACCESS]</h2>
            <p id="loginStorageName"></p>
            <input type="password" id="loginPassword" placeholder="enter password" onkeydown="if(event.key==='Enter') loginToStorage()">
            <div class="error" id="loginError">[ERROR] wrong password</div>
            <button class="btn" onclick="loginToStorage()">UNLOCK</button>
            <button class="btn btn-secondary" onclick="closeModal('loginModal')">CANCEL</button>
        </div>
    </div>
    
    <div class="modal" id="createModal">
        <div class="modal-content">
            <h2>[CREATE]</h2>
            <input type="text" id="newName" placeholder="storage name">
            <input type="text" id="newPath" placeholder="folder path (e.g. C:/Documents)">
            <input type="password" id="newPassword" placeholder="password">
            <div class="error" id="createError">[ERROR] fill all fields</div>
            <button class="btn" onclick="createStorage()">CREATE</button>
            <button class="btn btn-secondary" onclick="closeModal('createModal')">CANCEL</button>
        </div>
    </div>
    
    <script>
        let currentStorage = '';
        
        function openStorage(name) {
            currentStorage = name;
            document.getElementById('loginStorageName').textContent = 'storage: ' + name;
            document.getElementById('loginPassword').value = '';
            document.getElementById('loginError').style.display = 'none';
            document.getElementById('loginModal').classList.add('active');
        }
        
        function loginToStorage() {
            const password = document.getElementById('loginPassword').value;
            if (!password) {
                document.getElementById('loginError').textContent = '[ERROR] enter password';
                document.getElementById('loginError').style.display = 'block';
                return;
            }
            
            fetch('/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    storage: currentStorage,
                    password: password
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/storage/' + currentStorage;
                } else {
                    document.getElementById('loginError').textContent = '[ERROR] wrong password';
                    document.getElementById('loginError').style.display = 'block';
                }
            });
        }
        
        function showCreateModal() {
            document.getElementById('newName').value = '';
            document.getElementById('newPath').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('createError').style.display = 'none';
            document.getElementById('createModal').classList.add('active');
        }
        
        function createStorage() {
            const name = document.getElementById('newName').value.trim();
            const path = document.getElementById('newPath').value.trim();
            const password = document.getElementById('newPassword').value;
            
            if (!name || !path || !password) {
                document.getElementById('createError').style.display = 'block';
                return;
            }
            
            fetch('/create_storage', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: name,
                    path: path,
                    password: password
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    document.getElementById('createError').textContent = '[ERROR] ' + data.error;
                    document.getElementById('createError').style.display = 'block';
                }
            });
        }
        
        function closeModal(id) {
            document.getElementById(id).classList.remove('active');
        }
        
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', function(e) {
                if (e.target === this) {
                    this.classList.remove('active');
                }
            });
        });
    </script>
</body>
</html>
'''

STORAGE_PAGE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{{ storage_name }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
            background: #000;
            min-height: 100vh;
            padding: 15px;
            color: #fff;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: #111;
            border: 1px solid #2a2a2a;
            border-radius: 10px;
            padding: 25px 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
            flex-wrap: wrap;
            gap: 10px;
        }
        h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: #fff;
        }
        .header-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .btn-small {
            background: #1a1a1a;
            color: #888;
            border: 1px solid #2a2a2a;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        .btn-small:active {
            background: #222;
        }
        .breadcrumbs {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
            padding: 10px 0 14px 0;
            border-bottom: 1px solid #1a1a1a;
            margin-bottom: 18px;
            font-size: 13px;
            color: #666;
        }
        .breadcrumbs .crumb {
            color: #888;
            cursor: pointer;
            transition: color 0.2s;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .breadcrumbs .crumb:hover {
            color: #fff;
            background: #1a1a1a;
        }
        .breadcrumbs .crumb.current {
            color: #fff;
            font-weight: 600;
            cursor: default;
        }
        .breadcrumbs .sep {
            color: #333;
            padding: 0 2px;
        }
        .breadcrumbs .root {
            color: #44aaff;
        }
        .breadcrumbs .root:hover {
            color: #88ccff;
        }
        .upload-area {
            border: 2px dashed #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            background: #0a0a0a;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 18px;
            -webkit-tap-highlight-color: transparent;
        }
        .upload-area:active {
            background: #111;
            border-color: #444;
        }
        .upload-status {
        display: none;
        margin-top: 10px;
        background: #0a0a0a;
        border: 1px solid #1a1a1a;
        border-radius: 6px;
        padding: 12px 15px;
        }
        .upload-status.active {
            display: block;
        }
        .upload-status .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
            font-size: 12px;
            color: #888;
        }
        .upload-status .status-row .speed {
            color: #44aaff;
            font-weight: 600;
        }
        .upload-status .status-row .size {
            color: #aaa;
        }
        .upload-status .status-row .percent {
            color: #aa44ff;
            font-weight: 700;
            font-size: 14px;
        }
        .upload-status .file-name {
            color: #fff;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 4px;
            word-break: break-all;
        }
        .upload-status .progress-bar-custom {
            width: 100%;
            height: 4px;
            background: #1a1a1a;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 4px;
        }
        .upload-status .progress-bar-custom .fill {
            height: 100%;
            background: #1a6b3a;
            border-radius: 2px;
            width: 0%;
            transition: width 0.3s ease;
        }
        .upload-status .status-details {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            color: #555;
            margin-top: 4px;
        }
        .upload-status .status-details .uploaded {
            color: #44aa44;
        }
        .upload-status .status-details .remaining {
            color: #ff8844;
        }
        .upload-area input {
            display: none;
        }
        .upload-area .icon {
            font-size: 28px;
            color: #666;
            display: block;
            margin-bottom: 4px;
        }
        .upload-area .text {
            color: #888;
            font-size: 13px;
        }
        .file-list {
            margin-top: 12px;
        }
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            margin: 3px 0;
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 6px;
            transition: all 0.2s;
            flex-wrap: wrap;
            gap: 6px;
        }
        .file-item:active {
            background: #111;
        }
        .file-item.folder {
            border-color: #1a2a3a;
            cursor: pointer;
        }
        .file-item.folder:active {
            background: #111a22;
        }
        .file-item.folder .file-name {
            color: #88ccff;
        }
        .file-info {
            display: flex;
            align-items: center;
            gap: 10px;
            flex: 1;
            min-width: 100px;
        }
        .file-preview {
            width: 48px;
            height: 48px;
            border-radius: 4px;
            overflow: hidden;
            flex-shrink: 0;
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: #555;
        }
        .file-preview img, .file-preview video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .file-preview video {
            background: #000;
        }
        .file-details {
            display: flex;
            flex-direction: column;
            gap: 2px;
            flex: 1;
        }
        .file-name {
            font-weight: 500;
            color: #fff;
            font-size: 13px;
            word-break: break-word;
        }
        .file-meta {
            font-size: 10px;
            color: #555;
        }
        .file-actions {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        .file-actions .btn-action {
            padding: 4px 10px;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            cursor: pointer;
            font-size: 10px;
            transition: all 0.2s;
            background: #1a1a1a;
            color: #fff;
            text-decoration: none;
            -webkit-tap-highlight-color: transparent;
        }
        .file-actions .btn-action:active {
            background: #222;
        }
        .file-actions .btn-edit {
            border-color: #444;
            color: #88ccff;
        }
        .file-actions .btn-edit:active {
            background: #88ccff;
            color: #000;
        }
        .file-actions .btn-delete {
            border-color: #ff4444;
            color: #ff4444;
            background: transparent;
        }
        .file-actions .btn-delete:active {
            background: #ff4444;
            color: #fff;
        }
        .file-actions .btn-folder {
            border-color: #2a4a6a;
            color: #88ccff;
            background: transparent;
        }
        .file-actions .btn-view {
            border-color: #44aa44;
            color: #44aa44;
        }
        .file-actions .btn-view:active {
            background: #44aa44;
            color: #000;
        }
        .file-actions .btn-play {
            border-color: #aa44ff;
            color: #aa44ff;
        }
        .file-actions .btn-play:active {
            background: #aa44ff;
            color: #000;
        }
        .empty {
            color: #555;
            text-align: center;
            padding: 40px 20px;
            font-size: 14px;
            border: 1px dashed #222;
            border-radius: 8px;
            margin: 15px 0;
        }
        .progress {
            display: none;
            width: 100%;
            height: 3px;
            background: #1a1a1a;
            border-radius: 2px;
            margin-top: 12px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background: #666;
            width: 0%;
            transition: width 0.3s;
        }
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a1a;
            border: 1px solid #2a2a2a;
            color: #fff;
            padding: 10px 20px;
            border-radius: 8px;
            display: none;
            font-size: 12px;
            max-width: 90%;
            text-align: center;
            z-index: 2000;
        }
        .viewer-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.98);
            z-index: 4000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .viewer-overlay.active {
            display: flex;
        }
        .viewer-content {
            max-width: 90%;
            max-height: 90%;
            position: relative;
        }
        .viewer-content img, .viewer-content video {
            max-width: 100%;
            max-height: 85vh;
            border: 1px solid #2a2a2a;
            border-radius: 8px;
            display: block;
            margin: 0 auto;
        }
        .viewer-content video {
            background: #000;
        }
        .viewer-close {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1a1a1a;
            border: 1px solid #ff4444;
            color: #ff4444;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            z-index: 4001;
            -webkit-tap-highlight-color: transparent;
        }
        .viewer-close:active {
            background: #ff4444;
            color: #000;
        }
        .viewer-info {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: #888;
            font-size: 13px;
            background: rgba(0,0,0,0.8);
            padding: 8px 20px;
            border-radius: 6px;
            border: 1px solid #2a2a2a;
            text-align: center;
            z-index: 4001;
        }
        .player-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #0a0a0a;
            z-index: 3500;
            padding: 20px;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .player-overlay.active {
            display: flex;
        }
        .player-content {
            max-width: 500px;
            width: 100%;
            text-align: center;
        }
        .player-cover {
            width: 200px;
            height: 200px;
            border-radius: 12px;
            margin: 0 auto 20px;
            background: #1a1a1a;
            border: 2px solid #2a2a2a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 60px;
            color: #444;
            overflow: hidden;
        }
        .player-cover img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .player-info {
            margin-bottom: 20px;
        }
        .player-title {
            font-size: 20px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }
        .player-artist {
            font-size: 14px;
            color: #888;
        }
        .player-album {
            font-size: 12px;
            color: #555;
            margin-top: 2px;
        }
        .player-progress-container {
            width: 100%;
            margin: 15px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .player-time {
            font-size: 12px;
            color: #666;
            min-width: 40px;
        }
        .player-progress {
            flex: 1;
            height: 4px;
            background: #1a1a1a;
            border-radius: 2px;
            cursor: pointer;
            position: relative;
            transition: height 0.2s;
        }
        .player-progress:hover {
            height: 6px;
        }
        .player-progress-fill {
            height: 100%;
            background: #1a6b3a;
            border-radius: 2px;
            width: 0%;
            transition: width 0.1s;
        }
        .player-progress-dot {
            width: 12px;
            height: 12px;
            background: #aa44ff;
            border-radius: 50%;
            position: absolute;
            top: 50%;
            left: 0%;
            transform: translate(-50%, -50%);
            display: none;
        }
        .player-progress:hover .player-progress-dot {
            display: block;
        }
        .player-controls {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 25px;
            margin-top: 10px;
        }
        .player-controls button {
            background: transparent;
            border: 1px solid #2a2a2a;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            color: #fff;
            font-size: 20px;
            cursor: pointer;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .player-controls button:active {
            background: #1a1a1a;
            border-color: #444;
        }
        .player-controls .btn-play-main {
            width: 64px;
            height: 64px;
            font-size: 28px;
            border-color: #aa44ff;
            color: #aa44ff;
        }
        .player-controls .btn-play-main:active {
            background: #aa44ff;
            color: #000;
        }
        .player-volume {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 15px;
        }
        .player-volume input[type="range"] {
            width: 100px;
            height: 3px;
            -webkit-appearance: none;
            background: #1a1a1a;
            border-radius: 2px;
            outline: none;
        }
        .player-volume input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #aa44ff;
            cursor: pointer;
        }
        .player-volume input[type="range"]::-moz-range-thumb {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #aa44ff;
            cursor: pointer;
            border: none;
        }
        .player-close {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1a1a1a;
            border: 1px solid #ff4444;
            color: #ff4444;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            z-index: 3501;
            -webkit-tap-highlight-color: transparent;
        }

        .progress-info {
            display: none;
            margin-top: 8px;
            font-size: 12px;
            color: #888;
            text-align: center;
        }
        .progress-info.active {
            display: block;
        }
        .progress-status {
            display: flex;
            justify-content: space-between;
            padding: 0 4px;
        }
        .progress-count {
            color: #aaa;
        }
        .progress-percent {
            color: #aa44ff;
            font-weight: 600;
        }
        .player-close:active {
            background: #ff4444;
            color: #000;
        }
        .editor-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: #000;
            z-index: 3000;
            padding: 15px;
        }
        .editor-overlay.active {
            display: flex;
            flex-direction: column;
        }
        .editor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 12px;
            border-bottom: 1px solid #222;
            flex-wrap: wrap;
            gap: 8px;
        }
        .editor-header h2 {
            font-size: 15px;
            color: #fff;
            font-weight: 500;
        }
        .editor-actions {
            display: flex;
            gap: 8px;
        }
        .editor-actions button {
            padding: 5px 14px;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.2s;
            background: #1a1a1a;
            color: #fff;
            -webkit-tap-highlight-color: transparent;
        }
        .editor-actions button:active {
            background: #222;
        }
        .editor-actions .btn-save {
            border-color: #44aa44;
            color: #44aa44;
        }
        .editor-actions .btn-save:active {
            background: #44aa44;
            color: #000;
        }
        .editor-actions .btn-close-editor {
            border-color: #ff4444;
            color: #ff4444;
        }
        .editor-actions .btn-close-editor:active {
            background: #ff4444;
            color: #000;
        }
        .editor-body {
            flex: 1;
            margin-top: 10px;
        }
        .editor-body textarea {
            width: 100%;
            height: 100%;
            min-height: 350px;
            background: #0a0a0a;
            border: 1px solid #1a1a1a;
            border-radius: 6px;
            color: #ddd;
            font-size: 14px;
            font-family: 'Courier New', monospace;
            padding: 15px;
            resize: none;
            outline: none;
            line-height: 1.6;
        }
        .editor-body textarea:focus {
            border-color: #333;
        }
        .editor-body .word-toolbar {
            display: flex;
            gap: 4px;
            padding: 6px 0;
            flex-wrap: wrap;
            border-bottom: 1px solid #1a1a1a;
            margin-bottom: 10px;
        }
        .editor-body .word-toolbar button {
            padding: 3px 8px;
            border: 1px solid #2a2a2a;
            border-radius: 3px;
            cursor: pointer;
            font-size: 10px;
            background: #0a0a0a;
            color: #888;
            transition: all 0.2s;
            -webkit-tap-highlight-color: transparent;
        }
        .editor-body .word-toolbar button:active {
            background: #1a1a1a;
        }
        @media (max-width: 500px) {
            .container {
                padding: 18px 15px;
            }
            h1 {
                font-size: 18px;
            }
            .upload-area {
                padding: 15px;
            }
            .file-item {
                padding: 6px 8px;
            }
            .file-actions {
                width: 100%;
                justify-content: flex-end;
            }
            .file-preview {
                width: 36px;
                height: 36px;
            }
            .player-cover {
                width: 150px;
                height: 150px;
            }
            .player-title {
                font-size: 17px;
            }
            .player-controls button {
                width: 40px;
                height: 40px;
                font-size: 16px;
            }
            .player-controls .btn-play-main {
                width: 54px;
                height: 54px;
                font-size: 22px;
            }
            .editor-body textarea {
                min-height: 200px;
                font-size: 13px;
                padding: 10px;
            }
            .editor-overlay {
                padding: 10px;
            }
            .editor-header h2 {
                font-size: 13px;
            }
            .editor-actions button {
                padding: 4px 10px;
                font-size: 10px;
            }
            .breadcrumbs {
                font-size: 11px;
            }
            .viewer-close {
                top: 10px;
                right: 10px;
                padding: 6px 14px;
                font-size: 12px;
            }
            .viewer-info {
                font-size: 11px;
                padding: 6px 14px;
                bottom: 10px;
            }
            .player-close {
                top: 10px;
                right: 10px;
                padding: 6px 12px;
                font-size: 12px;
            }
            .player-volume input[type="range"] {
                width: 60px;
            }
        }
        @media (max-width: 380px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 14px 10px;
            }
            .file-actions .btn-action {
                padding: 3px 6px;
                font-size: 9px;
            }
            .file-preview {
                width: 28px;
                height: 28px;
            }
            .player-cover {
                width: 120px;
                height: 120px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>[ {{ storage_name }} ]</h1>
            <div class="header-actions">
                <button class="btn-small" onclick="location.href='/'">[exit]</button>
            </div>
        </div>
        
        <div class="breadcrumbs" id="breadcrumbs">
            <span class="crumb root" onclick="navigateTo('')">[root]</span>
            <span class="sep">></span>
            <span id="pathCrumbs"></span>
        </div>
        
        <div class="upload-area" onclick="document.getElementById('fileInput').click()">
            <span class="icon">[+]</span>
            <div class="text">upload files</div>
            <div class="text" style="font-size:11px;color:#444;">tap or drag & drop</div>
            <input type="file" id="fileInput" multiple>
        </div>
        
        <div class="progress" id="progress">
            <div class="progress-bar" id="progressBar"></div>
        </div>
 
        <div class="upload-status" id="uploadStatus">
            <div class="file-name" id="currentFileName">file.mp3</div>
            <div class="status-row">
                <span class="speed" id="uploadSpeed">0 KB/s</span>
                <span class="size" id="uploadSize">0 MB / 0 MB</span>
                <span class="percent" id="uploadPercent">0%</span>
            </div>
            <div class="progress-bar-custom">
                <div class="fill" id="uploadProgressFill"></div>
            </div>
            <div class="status-details">
                <span class="uploaded" id="uploadedCount">0 files uploaded</span>
                <span class="remaining" id="remainingCount">0 remaining</span>
            </div>
        </div>
        
        <div class="file-list" id="fileList">
            <div class="empty">[ loading... ]</div>
        </div>
    </div>
    
    <div class="viewer-overlay" id="viewerOverlay" onclick="closeViewer(event)">
        <button class="viewer-close" onclick="closeViewer()">[x]</button>
        <div class="viewer-content" id="viewerContent"></div>
        <div class="viewer-info" id="viewerInfo"></div>
    </div>
    
    <div class="player-overlay" id="playerOverlay">
        <button class="player-close" onclick="closePlayer()">[x]</button>
        <div class="player-content">
            <div class="player-cover" id="playerCover">[♪]</div>
            <div class="player-info">
                <div class="player-title" id="playerTitle">Track Name</div>
                <div class="player-artist" id="playerArtist">Artist</div>
                <div class="player-album" id="playerAlbum">Album</div>
            </div>
            <div class="player-progress-container">
                <span class="player-time" id="playerCurrentTime">0:00</span>
                <div class="player-progress" id="playerProgress" onclick="seekAudio(event)">
                    <div class="player-progress-fill" id="playerProgressFill"></div>
                    <div class="player-progress-dot" id="playerProgressDot"></div>
                </div>
                <span class="player-time" id="playerDuration">0:00</span>
            </div>
            <div class="player-controls">
                <button onclick="prevTrack()">⏮</button>
                <button class="btn-play-main" id="playerPlayBtn" onclick="togglePlay()">▶</button>
                <button onclick="nextTrack()">⏭</button>
            </div>
            <div class="player-volume">
                <span style="color:#666;font-size:14px;">🔊</span>
                <input type="range" min="0" max="1" step="0.01" value="1" id="playerVolume" oninput="setVolume(this.value)">
            </div>
        </div>
        <audio id="playerAudio" style="display:none;"></audio>
    </div>
    
    <div class="editor-overlay" id="editorOverlay">
        <div class="editor-header">
            <h2 id="editorFileName">[edit]</h2>
            <div class="editor-actions">
                <button class="btn-save" onclick="saveFile()">[save]</button>
                <button class="btn-close-editor" onclick="closeEditor()">[x]</button>
            </div>
        </div>
        <div class="editor-body">
            <div class="word-toolbar">
                <button onclick="wrapText('**','**')">[B]</button>
                <button onclick="wrapText('_','_')">[I]</button>
                <button onclick="wrapText('```\\n','\\n```')">[code]</button>
                <button onclick="wrapText('# ','')">[h1]</button>
                <button onclick="wrapText('## ','')">[h2]</button>
                <button onclick="wrapText('### ','')">[h3]</button>
                <button onclick="wrapText('- ','')">[list]</button>
                <button onclick="wrapText('> ','')">[quote]</button>
                <button onclick="insertDate()">[date]</button>
            </div>
            <textarea id="editorContent" spellcheck="true"></textarea>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <script>
    let currentPath = '';
    let currentStorage = '{{ storage_name }}';
    let currentEditFile = '';
    let audioFiles = [];
    let currentTrackIndex = 0;
    let isPlaying = false;
    let uploadStartTime = 0;
    let lastLoaded = 0;
    let lastTime = 0;
    let speedSamples = [];

    function updateUploadStatus(uploaded, total, loaded, totalSize, currentFile) {
        const status = document.getElementById('uploadStatus');
        status.classList.add('active');
        
        const percent = totalSize > 0 ? (loaded / totalSize) * 100 : 0;
        const remaining = total - uploaded;
        
        document.getElementById('currentFileName').textContent = currentFile || 'Uploading...';
        document.getElementById('uploadPercent').textContent = Math.round(percent) + '%';
        document.getElementById('uploadProgressFill').style.width = percent + '%';
        document.getElementById('uploadedCount').textContent = uploaded + ' files uploaded';
        document.getElementById('remainingCount').textContent = remaining + ' remaining';
        
        const loadedMB = (loaded / (1024 * 1024)).toFixed(1);
        const totalMB = (totalSize / (1024 * 1024)).toFixed(1);
        document.getElementById('uploadSize').textContent = loadedMB + ' MB / ' + totalMB + ' MB';
    }

    function updateSpeed(loaded) {
        const now = Date.now();
        const timeDiff = (now - lastTime) / 1000;
        
        if (timeDiff >= 0.5) {
            const bytesDiff = loaded - lastLoaded;
            const speed = bytesDiff / timeDiff;
            
            speedSamples.push(speed);
            if (speedSamples.length > 5) speedSamples.shift();
            
            const avgSpeed = speedSamples.reduce((a, b) => a + b, 0) / speedSamples.length;
            
            let speedStr;
            if (avgSpeed > 1024 * 1024) {
                speedStr = (avgSpeed / (1024 * 1024)).toFixed(1) + ' MB/s';
            } else if (avgSpeed > 1024) {
                speedStr = (avgSpeed / 1024).toFixed(0) + ' KB/s';
            } else {
                speedStr = avgSpeed.toFixed(0) + ' B/s';
            }
            
            document.getElementById('uploadSpeed').textContent = speedStr;
            
            lastLoaded = loaded;
            lastTime = now;
        }
    }

    function uploadFiles() {
        const files = document.getElementById('fileInput').files;
        if (files.length === 0) {
            showToast('[WARNING] select files');
            return;
        }
        
        const totalFiles = files.length;
        let totalSize = 0;
        for (let file of files) {
            totalSize += file.size;
        }
        
        speedSamples = [];
        lastLoaded = 0;
        lastTime = Date.now();
        
        const status = document.getElementById('uploadStatus');
        status.classList.add('active');
        
        const formData = new FormData();
        for (let file of files) {
            formData.append('files', file);
        }
        formData.append('path', currentPath);
        
        const xhr = new XMLHttpRequest();
        let currentFileIndex = 0;
        
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                
                const fileProgress = (e.loaded / e.total);
                const uploadedCount = Math.floor(fileProgress * totalFiles);
                
                const fileName = files[currentFileIndex] ? files[currentFileIndex].name : 'Complete';
                
                updateUploadStatus(
                    uploadedCount, 
                    totalFiles, 
                    e.loaded, 
                    e.total, 
                    fileName
                );
                
                updateSpeed(e.loaded);
                
                document.getElementById('uploadProgressFill').style.width = percentComplete + '%';
            }
        });
        
        xhr.onload = function() {
            status.classList.remove('active');
            
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.success) {
                    showToast(`[OK] Uploaded ${data.uploaded}/${data.total} files`);
                    if (data.errors && data.errors.length > 0) {
                        showToast(`[WARNING] ${data.errors.length} files failed`);
                    }
                } else {
                    showToast(`[ERROR] Upload failed: ${data.error || 'unknown error'}`);
                }
            } else {
                showToast('[ERROR] Upload failed');
            }
            
            document.getElementById('fileInput').value = '';
            loadFiles(currentPath);
        };
        
        xhr.onerror = function() {
            status.classList.remove('active');
            showToast('[ERROR] Upload failed');
            document.getElementById('fileInput').value = '';
        };
        
        xhr.open('POST', '/upload_progress/' + currentStorage);
        xhr.send(formData);
    }

    function loadFiles(path) {
        currentPath = path || '';
        const url = '/files/' + currentStorage + '?path=' + encodeURIComponent(currentPath);
        
        fetch(url)
            .then(res => res.json())
            .then(data => {
                const files = data.files || [];
                const currentPathDisplay = data.current_path || '';
                const fullPath = data.full_path || '';
                
                updateBreadcrumbs(currentPathDisplay, fullPath);
                
                const container = document.getElementById('fileList');
                if (files.length === 0) {
                    container.innerHTML = '<div class="empty">[ empty ]</div>';
                    return;
                }
                
                audioFiles = files.filter(f => f.is_audio).map(f => f.name);
                
                let html = '';
                const folders = files.filter(f => f.is_dir);
                const items = files.filter(f => !f.is_dir);
                
                folders.forEach(folder => {
                    const newPath = currentPath ? currentPath + '/' + folder.name : folder.name;
                    html += `
                        <div class="file-item folder" onclick="navigateTo('${newPath}')">
                            <div class="file-info">
                                <div class="file-preview">[D]</div>
                                <div class="file-details">
                                    <span class="file-name">${folder.name}</span>
                                    <span class="file-meta">folder</span>
                                </div>
                            </div>
                            <div class="file-actions">
                                <button class="btn-action btn-folder" onclick="event.stopPropagation();navigateTo('${newPath}')">[open]</button>
                            </div>
                        </div>
                    `;
                });
                
                items.forEach(file => {
                    const filePath = currentPath ? currentPath + '/' + file.name : file.name;
                    const isText = file.name.match(/\\.(txt|md|py|js|html|css|json|xml|sql|sh|log|cpp|c|h|java|go|rs|rb|php|conf|ini|cfg)$/i);
                    const isImage = file.name.match(/\\.(png|jpg|jpeg|gif|webp|bmp|svg|ico)$/i);
                    const isVideo = file.name.match(/\\.(mp4|webm|avi|mov|mkv|flv|wmv|m4v)$/i);
                    const isAudio = file.is_audio;
                    const isMedia = isImage || isVideo;
                    
                    let previewHtml = '';
                    if (isImage) {
                        previewHtml = `<img src="/view/${currentStorage}/${filePath}" alt="preview" loading="lazy" onerror="this.parentElement.innerHTML='[img]'">`;
                    } else if (isVideo) {
                        previewHtml = `<video src="/view/${currentStorage}/${filePath}" muted preload="metadata" onerror="this.parentElement.innerHTML='[vid]'"></video>`;
                    } else if (isAudio) {
                        previewHtml = '[♪]';
                    } else {
                        previewHtml = '[F]';
                    }
                    
                    let actionButtons = '';
                    if (isMedia) {
                        actionButtons += `<button class="btn-action btn-view" onclick="viewFile('${filePath}','${isVideo ? 'video' : 'image'}')">[view]</button>`;
                    }
                    if (isAudio) {
                        const trackIndex = audioFiles.indexOf(file.name);
                        actionButtons += `<button class="btn-action btn-play" onclick="playTrack(${trackIndex})">[play]</button>`;
                    }
                    if (isText) {
                        actionButtons += `<button class="btn-action btn-edit" onclick="openEditor('${filePath}')">[edit]</button>`;
                    }
                    actionButtons += `<a href="/download/${currentStorage}/${filePath}" class="btn-action">[get]</a>`;
                    actionButtons += `<button class="btn-action btn-delete" onclick="deleteFile('${filePath}')">[x]</button>`;
                    
                    html += `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-preview">${previewHtml}</div>
                                <div class="file-details">
                                    <span class="file-name">${file.name}</span>
                                    <span class="file-meta">${file.size}  |  ${file.date}</span>
                                    ${isAudio ? `<span class="file-meta" style="color:#aa44ff;">[audio] ${file.audio_info || ''}</span>` : ''}
                                </div>
                            </div>
                            <div class="file-actions">
                                ${actionButtons}
                            </div>
                        </div>
                    `;
                });
                
                container.innerHTML = html;
            })
            .catch(() => {
                document.getElementById('fileList').innerHTML = '<div class="empty">[ERROR] failed to load</div>';
            });
    }

    function updateBreadcrumbs(currentPath, fullPath) {
        const container = document.getElementById('pathCrumbs');
        if (!currentPath || currentPath === '') {
            container.innerHTML = '<span class="crumb current">[root]</span>';
            return;
        }
        
        const parts = currentPath.split('/');
        let html = '';
        let pathAccum = '';
        
        parts.forEach((part, index) => {
            pathAccum += (index === 0 ? '' : '/') + part;
            const isLast = index === parts.length - 1;
            if (isLast) {
                html += `<span class="crumb current">${part}</span>`;
            } else {
                html += `<span class="crumb" onclick="navigateTo('${pathAccum}')">${part}</span>`;
                html += `<span class="sep">></span>`;
            }
        });
        
        container.innerHTML = html;
    }

    function navigateTo(path) {
        loadFiles(path);
    }

    function viewFile(filepath, type) {
        const viewer = document.getElementById('viewerOverlay');
        const content = document.getElementById('viewerContent');
        const info = document.getElementById('viewerInfo');
        
        const url = '/view/' + currentStorage + '/' + filepath;
        info.textContent = filepath;
        
        if (type === 'video') {
            content.innerHTML = `<video src="${url}" controls autoplay></video>`;
        } else {
            content.innerHTML = `<img src="${url}" alt="${filepath}">`;
        }
        
        viewer.classList.add('active');
    }

    function closeViewer(e) {
        if (e && e.target !== e.currentTarget) return;
        document.getElementById('viewerOverlay').classList.remove('active');
        document.getElementById('viewerContent').innerHTML = '';
    }

    function playTrack(index) {
        currentTrackIndex = index;
        const file = audioFiles[index];
        const filePath = currentPath ? currentPath + '/' + file : file;
        
        fetch('/metadata/' + currentStorage + '/' + filePath)
            .then(res => res.json())
            .then(data => {
                document.getElementById('playerTitle').textContent = data.title || file;
                document.getElementById('playerArtist').textContent = data.artist || 'Unknown';
                document.getElementById('playerAlbum').textContent = data.album || '';
                
                const coverEl = document.getElementById('playerCover');
                if (data.has_cover) {
                    coverEl.innerHTML = `<img src="/cover/${currentStorage}/${filePath}">`;
                } else {
                    coverEl.innerHTML = '[♪]';
                }
            })
            .catch(() => {
                document.getElementById('playerTitle').textContent = file;
                document.getElementById('playerArtist').textContent = 'Unknown';
                document.getElementById('playerAlbum').textContent = '';
            });
        
        const audio = document.getElementById('playerAudio');
        audio.src = '/view/' + currentStorage + '/' + filePath;
        audio.load();
        audio.play();
        isPlaying = true;
        document.getElementById('playerPlayBtn').textContent = '⏸';
        
        document.getElementById('playerOverlay').classList.add('active');
        
        audio.onloadedmetadata = function() {
            document.getElementById('playerDuration').textContent = formatTime(audio.duration);
        };
        
        audio.ontimeupdate = function() {
            const progress = (audio.currentTime / audio.duration) * 100;
            document.getElementById('playerProgressFill').style.width = progress + '%';
            document.getElementById('playerProgressDot').style.left = progress + '%';
            document.getElementById('playerCurrentTime').textContent = formatTime(audio.currentTime);
        };
        
        audio.onended = function() {
            nextTrack();
        };
    }

    function togglePlay() {
        const audio = document.getElementById('playerAudio');
        if (audio.paused) {
            audio.play();
            isPlaying = true;
            document.getElementById('playerPlayBtn').textContent = '⏸';
        } else {
            audio.pause();
            isPlaying = false;
            document.getElementById('playerPlayBtn').textContent = '▶';
        }
    }

    function prevTrack() {
        if (audioFiles.length === 0) return;
        currentTrackIndex = (currentTrackIndex - 1 + audioFiles.length) % audioFiles.length;
        playTrack(currentTrackIndex);
    }

    function nextTrack() {
        if (audioFiles.length === 0) return;
        currentTrackIndex = (currentTrackIndex + 1) % audioFiles.length;
        playTrack(currentTrackIndex);
    }

    function seekAudio(e) {
        const progressBar = document.getElementById('playerProgress');
        const rect = progressBar.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width;
        const audio = document.getElementById('playerAudio');
        audio.currentTime = x * audio.duration;
    }

    function setVolume(value) {
        document.getElementById('playerAudio').volume = value;
    }

    function formatTime(seconds) {
        if (isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return mins + ':' + (secs < 10 ? '0' : '') + secs;
    }

    function closePlayer() {
        document.getElementById('playerOverlay').classList.remove('active');
        const audio = document.getElementById('playerAudio');
        audio.pause();
        audio.src = '';
        isPlaying = false;
        document.getElementById('playerPlayBtn').textContent = '▶';
    }

    function openEditor(filepath) {
        currentEditFile = filepath;
        const name = filepath.split('/').pop();
        document.getElementById('editorFileName').textContent = '[edit] ' + name;
        document.getElementById('editorContent').value = '[loading...]';
        document.getElementById('editorOverlay').classList.add('active');
        
        fetch('/read/' + currentStorage + '/' + filepath)
            .then(res => res.text())
            .then(content => {
                document.getElementById('editorContent').value = content;
            })
            .catch(() => {
                document.getElementById('editorContent').value = '[ERROR] could not load file';
            });
    }

    function saveFile() {
        const content = document.getElementById('editorContent').value;
        fetch('/save/' + currentStorage + '/' + currentEditFile, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content: content})
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast('[OK] file saved');
                loadFiles(currentPath);
            } else {
                showToast('[ERROR] ' + data.error);
            }
        });
    }

    function closeEditor() {
        document.getElementById('editorOverlay').classList.remove('active');
        loadFiles(currentPath);
    }

    function wrapText(prefix, suffix) {
        const textarea = document.getElementById('editorContent');
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selected = textarea.value.substring(start, end);
        const before = textarea.value.substring(0, start);
        const after = textarea.value.substring(end);
        
        textarea.value = before + prefix + selected + suffix + after;
        textarea.focus();
        textarea.selectionStart = start + prefix.length;
        textarea.selectionEnd = end + prefix.length;
    }

    function insertDate() {
        const now = new Date();
        const dateStr = now.toLocaleString();
        const textarea = document.getElementById('editorContent');
        const start = textarea.selectionStart;
        const before = textarea.value.substring(0, start);
        const after = textarea.value.substring(start);
        textarea.value = before + dateStr + after;
        textarea.focus();
        textarea.selectionStart = start + dateStr.length;
        textarea.selectionEnd = start + dateStr.length;
    }

    function deleteFile(filepath) {
        if (!confirm('[CONFIRM] delete "' + filepath + '"?')) return;
        
        fetch('/delete/' + currentStorage + '/' + filepath, { method: 'DELETE' })
            .then(res => res.json())
            .then(data => {
                showToast('[OK] ' + data.message);
                loadFiles(currentPath);
            });
    }

    function showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }

    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            if (document.getElementById('editorOverlay').classList.contains('active')) {
                saveFile();
            }
        }
        if (e.key === 'Escape') {
            if (document.getElementById('editorOverlay').classList.contains('active')) {
                closeEditor();
            }
            if (document.getElementById('viewerOverlay').classList.contains('active')) {
                closeViewer();
            }
            if (document.getElementById('playerOverlay').classList.contains('active')) {
                closePlayer();
            }
        }
        if (document.getElementById('playerOverlay').classList.contains('active')) {
            if (e.key === ' ') {
                e.preventDefault();
                togglePlay();
            }
            if (e.key === 'ArrowLeft') {
                const audio = document.getElementById('playerAudio');
                audio.currentTime = Math.max(0, audio.currentTime - 5);
            }
            if (e.key === 'ArrowRight') {
                const audio = document.getElementById('playerAudio');
                audio.currentTime = Math.min(audio.duration, audio.currentTime + 5);
            }
        }
    });

    document.querySelector('.upload-area').addEventListener('dragover', (e) => {
        e.preventDefault();
        e.currentTarget.style.borderColor = '#444';
    });

    document.querySelector('.upload-area').addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.currentTarget.style.borderColor = '#2a2a2a';
    });

    document.querySelector('.upload-area').addEventListener('drop', (e) => {
        e.preventDefault();
        e.currentTarget.style.borderColor = '#2a2a2a';
        document.getElementById('fileInput').files = e.dataTransfer.files;
        uploadFiles();
    });

    document.getElementById('fileInput').addEventListener('change', function(e) {
        const files = e.target.files;
        if (files.length > 0) {
            let totalSize = 0;
            for (let file of files) {
                totalSize += file.size;
            }
            const sizeMB = (totalSize / (1024 * 1024)).toFixed(1);
            showToast(`[SELECTED] ${files.length} files (${sizeMB} MB)`);
            uploadFiles();
        }
    });

    loadFiles('');
</script>
</body>
</html>
'''

@app.route('/')
def index():
    storages = load_storages()
    return render_template_string(MAIN_PAGE, storages=storages)

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    storage_name = data.get('storage')
    password = data.get('password')
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'success': False, 'error': 'Storage not found'})
    
    if storages[storage_name]['password'] == hash_password(password):
        session['logged_in'] = True
        session['current_storage'] = storage_name
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Wrong password'})

@app.route('/create_storage', methods=['POST'])
def create_storage():
    data = request.json
    name = data.get('name')
    path = data.get('path')
    password = data.get('password')
    
    if not name or not path or not password:
        return jsonify({'success': False, 'error': 'Fill all fields'})
    
    storages = load_storages()
    if name in storages:
        return jsonify({'success': False, 'error': 'Storage already exists'})
    
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            return jsonify({'success': False, 'error': 'Cannot create folder'})
    
    create_storage_structure(path)
    
    storages[name] = {
        'path': path,
        'password': hash_password(password)
    }
    save_storages(storages)
    return jsonify({'success': True})

@app.route('/storage/<storage_name>')
def storage_page(storage_name):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return redirect(url_for('index'))
    
    storages = load_storages()
    if storage_name not in storages:
        return redirect(url_for('index'))
    
    return render_template_string(STORAGE_PAGE, 
                                 storage_name=storage_name,
                                 storage_path=storages[storage_name]['path'])

@app.route('/files/<storage_name>')
def list_files(storage_name):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({'files': [], 'current_path': '', 'full_path': ''})
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'files': [], 'current_path': '', 'full_path': ''})
    
    base_path = storages[storage_name]['path']
    subpath = request.args.get('path', '')
    
    if '..' in subpath or subpath.startswith('/') or subpath.startswith('\\\\'):
        return jsonify({'files': [], 'current_path': '', 'full_path': ''})
    
    current_path = os.path.join(base_path, subpath) if subpath else base_path
    
    if not os.path.exists(current_path):
        return jsonify({'files': [], 'current_path': subpath, 'full_path': current_path})
    
    audio_extensions = ['.mp3', '.flac', '.ogg', '.oga', '.m4a', '.mp4', '.wav', '.aif', '.aiff', '.ape']
    
    files = []
    try:
        for item in os.listdir(current_path):
            item_path = os.path.join(current_path, item)
            if os.path.isdir(item_path):
                files.append({
                    'name': item,
                    'is_dir': True,
                    'size': '',
                    'date': '',
                    'is_audio': False,
                    'audio_info': ''
                })
            else:
                size = os.path.getsize(item_path)
                if size < 1024:
                    size_str = str(size) + ' B'
                elif size < 1024 * 1024:
                    size_str = str(round(size / 1024, 1)) + ' KB'
                else:
                    size_str = str(round(size / (1024 * 1024), 1)) + ' MB'
                
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(item_path))
                date_str = mod_time.strftime("%d.%m.%Y %H:%M")
                
                ext = os.path.splitext(item)[1].lower()
                is_audio = ext in audio_extensions
                audio_info = ''
                
                if is_audio:
                    try:
                        meta = get_audio_metadata(item_path)
                        if meta.get('title') and meta.get('artist'):
                            audio_info = meta['artist'] + ' - ' + meta['title']
                        elif meta.get('title'):
                            audio_info = meta['title']
                        if meta.get('duration'):
                            dur = meta['duration']
                            mins = dur // 60
                            secs = dur % 60
                            audio_info += f' ({mins}:{secs:02d})'
                    except:
                        audio_info = ''
                
                files.append({
                    'name': item,
                    'is_dir': False,
                    'size': size_str,
                    'date': date_str,
                    'is_audio': is_audio,
                    'audio_info': audio_info
                })
    except:
        pass
    
    files.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    return jsonify({
        'files': files,
        'current_path': subpath,
        'full_path': current_path
    })

@app.route('/upload/<storage_name>', methods=['POST'])
def upload_files(storage_name):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({'count': 0})
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'count': 0})
    
    base_path = storages[storage_name]['path']
    subpath = request.form.get('path', '')
    
    if '..' in subpath or subpath.startswith('/') or subpath.startswith('\\\\'):
        return jsonify({'count': 0})
    
    upload_path = os.path.join(base_path, subpath) if subpath else base_path
    
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    
    files = request.files.getlist('files')
    count = 0
    
    for file in files:
        if file.filename:
            file.save(os.path.join(upload_path, file.filename))
            count += 1
    
    return jsonify({'count': count})

@app.route('/metadata/<storage_name>/<path:filename>')
def get_metadata(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({})
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({})
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return jsonify({})
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            meta = get_audio_metadata(file_path)
            return jsonify(meta)
        except:
            return jsonify({})
    
    return jsonify({})

@app.route('/cover/<storage_name>/<path:filename>')
def get_cover(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return 'Unauthorized', 401
    
    storages = load_storages()
    if storage_name not in storages:
        return 'Storage not found', 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return 'Access denied', 403
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.mp3']:
                audio = MP3(file_path)
                if 'APIC:' in audio:
                    img = audio['APIC:']
                    return img.data, 200, {'Content-Type': img.mime}
                elif 'APIC' in audio:
                    img = audio['APIC']
                    return img.data, 200, {'Content-Type': img.mime}
            elif ext in ['.flac']:
                audio = FLAC(file_path)
                if audio.pictures:
                    img = audio.pictures[0]
                    return img.data, 200, {'Content-Type': img.mime}
            elif ext in ['.m4a', '.mp4']:
                audio = MP4(file_path)
                if 'covr' in audio:
                    img = audio['covr'][0]
                    return img, 200, {'Content-Type': 'image/jpeg'}
        except:
            pass
    
    return '', 404

@app.route('/view/<storage_name>/<path:filename>')
def view_file(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return 'Unauthorized', 401
    
    storages = load_storages()
    if storage_name not in storages:
        return 'Storage not found', 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return 'Access denied', 403
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        mimetype, _ = mimetypes.guess_type(file_path)
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), mimetype=mimetype)
    
    return 'File not found', 404

@app.route('/download/<storage_name>/<path:filename>')
def download_file(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return 'Unauthorized', 401
    
    storages = load_storages()
    if storage_name not in storages:
        return 'Storage not found', 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return 'Access denied', 403
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path))
    
    return 'File not found', 404

@app.route('/delete/<storage_name>/<path:filename>', methods=['DELETE'])
def delete_file(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({'error': 'Unauthorized'}), 401
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'error': 'Storage not found'}), 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return jsonify({'error': 'Access denied'}), 403
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path):
        if os.path.isdir(file_path):
            try:
                os.rmdir(file_path)
                return jsonify({'message': 'Folder deleted'})
            except:
                return jsonify({'error': 'Folder not empty'}), 400
        else:
            os.remove(file_path)
            return jsonify({'message': 'File deleted'})
    
    return jsonify({'error': 'Not found'}), 404

@app.route('/read/<storage_name>/<path:filename>')
def read_file(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return 'Unauthorized', 401
    
    storages = load_storages()
    if storage_name not in storages:
        return 'Storage not found', 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return 'Access denied', 403
    
    file_path = os.path.join(base_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return '[ERROR] cannot read file'
    
    return '[ERROR] file not found'

@app.route('/upload_progress/<storage_name>', methods=['POST'])
def upload_files_progress(storage_name):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({'error': 'Unauthorized'}), 401
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'error': 'Storage not found'}), 404
    
    base_path = storages[storage_name]['path']
    subpath = request.form.get('path', '')
    
    if '..' in subpath or subpath.startswith('/') or subpath.startswith('\\\\'):
        return jsonify({'error': 'Access denied'}), 403
    
    upload_path = os.path.join(base_path, subpath) if subpath else base_path
    
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, exist_ok=True)
    
    files = request.files.getlist('files')
    total = len(files)
    uploaded = 0
    errors = []
    
    for file in files:
        if file.filename:
            try:
                file.save(os.path.join(upload_path, file.filename))
                uploaded += 1
            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")
    
    return jsonify({
        'total': total,
        'uploaded': uploaded,
        'remaining': total - uploaded,
        'errors': errors,
        'success': len(errors) == 0
    })

@app.route('/save/<storage_name>/<path:filename>', methods=['POST'])
def save_file(storage_name, filename):
    if not session.get('logged_in') or session.get('current_storage') != storage_name:
        return jsonify({'error': 'Unauthorized'}), 401
    
    storages = load_storages()
    if storage_name not in storages:
        return jsonify({'error': 'Storage not found'}), 404
    
    base_path = storages[storage_name]['path']
    
    if '..' in filename or filename.startswith('/') or filename.startswith('\\\\'):
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    content = data.get('content', '')
    file_path = os.path.join(base_path, filename)
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "_"*50)
    print(" ")
    print("FILE STORAGE SERVER v5")
    print("_"*50)
    print("\n[ACCESS] On this computer:")
    print("   http://localhost:8000")
    print("\n[ACCESS] On other devices:")
    print("   http://" + local_ip + ":8000")
    print("\n[INFO] Config file: " + CONFIG_FILE)
    print("\n[STOP] Press Ctrl+C")
    print("_"*50 + "\n")
    
    app.run(host='0.0.0.0', port=8000, debug=False)
