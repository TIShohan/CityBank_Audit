import streamlit as st
import os
import threading
import socketserver
import http.server
import socket
import base64
from tkinter import filedialog, Tk

# --- PAGE CONFIG ---
st.set_page_config(page_title="City Bank Video Reviewer", page_icon="🎥", layout="wide")

# --- STYLE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    
    .main {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    
    .stTextInput > div > div > input {
        background-color: #0f3460;
        color: white;
        border: 1px solid #e94560;
        border-radius: 10px;
    }
    
    .video-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 20px;
        margin-top: 20px;
    }
    
    .title-text {
        text-align: center;
        background: -webkit-linear-gradient(#e94560, #950740);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONFIG & SERVER ---
if 'base_path' not in st.session_state:
    st.session_state.base_path = r"D:\City Bank_Downloads"

class PathConfig:
    def __init__(self, path):
        self.path = path

if 'path_config' not in st.session_state:
    st.session_state.path_config = PathConfig(st.session_state.base_path)

def select_folder():
    try:
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory(master=root)
        root.destroy()
        return path
    except:
        return None

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Adds support for Range requests (required for video seeking)."""
    def __init__(self, *args, **kwargs):
        self.path_config = kwargs.pop('path_config')
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        # Ensure we serve files from the current dynamic base_path
        path = super().translate_path(path)
        rel_path = os.path.relpath(path, os.getcwd())
        return os.path.join(self.path_config.path, rel_path)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def do_GET(self):
        if 'Range' in self.headers:
            self.handle_range_request()
        else:
            super().do_GET()

    def handle_range_request(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            self.send_error(404)
            return

        file_size = os.path.getsize(path)
        range_header = self.headers.get('Range')
        
        # Simple Range parser
        try:
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
        except:
            self.send_error(400, "Invalid Range")
            return

        if start >= file_size or end >= file_size or start > end:
            self.send_error(416, "Requested Range Not Satisfiable")
            return

        content_length = end - start + 1
        
        self.send_response(206)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
        self.send_header('Content-Length', str(content_length))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        with open(path, 'rb') as f:
            f.seek(start)
            self.wfile.write(f.read(content_length))

def start_server(port, path_config):
    def handler_factory(*args, **kwargs):
        return RangeRequestHandler(*args, path_config=path_config, **kwargs)
    
    with socketserver.TCPServer(("", port), handler_factory) as httpd:
        httpd.serve_forever()

if 'port' not in st.session_state:
    port = find_free_port()
    st.session_state.port = port
    thread = threading.Thread(target=start_server, args=(port, st.session_state.path_config), daemon=True)
    thread.start()

# --- UI ---
st.markdown('<h1 class="title-text">🎥 Side-by-Side Video Reviewer</h1>', unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("### 📁 Video Source")
col_path, col_browse = st.sidebar.columns([3, 1])
with col_path:
    new_path = st.sidebar.text_input("Source Path", st.session_state.base_path, label_visibility="collapsed")
    if new_path != st.session_state.base_path:
        st.session_state.base_path = new_path
        st.session_state.path_config.path = new_path
with col_browse:
    if st.sidebar.button("📁"):
        selected = select_folder()
        if selected:
            st.session_state.base_path = selected
            st.session_state.path_config.path = selected
            st.rerun()

# --- DISCOVER CANDIDATES ---
candidate_list = []
if os.path.exists(st.session_state.base_path):
    candidate_list = [d for d in os.listdir(st.session_state.base_path) if os.path.isdir(os.path.join(st.session_state.base_path, d))]

st.sidebar.info(f"Currently viewing: \n`{st.session_state.base_path}`")
st.sidebar.divider()
selected_cand = st.sidebar.selectbox("Select Candidate", ["None"] + sorted(candidate_list), index=0)

cand_id = st.text_input("Candidate ID", value=selected_cand if selected_cand != "None" else "", help="Type or select a candidate folder")

if cand_id:
    # URL construction
    v1_rel_path = f"{cand_id}/{cand_id}_screenrecord.mp4"
    v2_rel_path = f"{cand_id}/{cand_id}_webcam.mp4"
    
    v1_full_path = os.path.join(st.session_state.base_path, v1_rel_path)
    v2_full_path = os.path.join(st.session_state.base_path, v2_rel_path)
    
    if os.path.exists(v1_full_path) and os.path.exists(v2_full_path):
        v1_url = f"http://localhost:{st.session_state.port}/{v1_rel_path}"
        v2_url = f"http://localhost:{st.session_state.port}/{v2_rel_path}"
        
        # Synchronized Player HTML/JS
        html_code = f"""
        <div id="wrapper" style="display: flex; flex-direction: column; align-items: center; gap: 20px; background: #0f172a; padding: 20px; border-radius: 15px; color: white;">
            <div style="display: flex; gap: 15px; width: 100%; justify-content: center;">
                <!-- Video 1 -->
                <div style="flex: 1; position: relative; border: 2px solid #334155; border-radius: 10px; overflow: hidden;">
                    <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; z-index: 10;">SCREEN RECORD</div>
                    <video id="v1" width="100%" style="background: black;">
                        <source src="{v1_url}" type="video/mp4">
                    </video>
                    <div style="padding: 10px; background: #1e293b; display: flex; align-items: center; gap: 15px;">
                        <button id="mute1" style="background: #e94560; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer; font-size: 12px;">Mute</button>
                        <input type="range" id="vol1" min="0" max="1" step="0.1" value="1" style="flex: 1; height: 5px; cursor: pointer;">
                        <span id="volLab1" style="font-size: 12px; font-family: monospace; min-width: 35px;">100%</span>
                    </div>
                </div>
                
                <!-- Video 2 -->
                <div style="flex: 1; position: relative; border: 2px solid #334155; border-radius: 10px; overflow: hidden;">
                    <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; z-index: 10;">WEBCAM RECORD</div>
                    <video id="v2" width="100%" style="background: black;">
                        <source src="{v2_url}" type="video/mp4">
                    </video>
                    <div style="padding: 10px; background: #1e293b; display: flex; align-items: center; gap: 15px;">
                        <button id="mute2" style="background: #e94560; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer; font-size: 12px;">Mute</button>
                        <input type="range" id="vol2" min="0" max="1" step="0.1" value="1" style="flex: 1; height: 5px; cursor: pointer;">
                        <span id="volLab2" style="font-size: 12px; font-family: monospace; min-width: 35px;">100%</span>
                    </div>
                </div>
            </div>

            <!-- Global Controls -->
            <div style="width: 100%; background: #1e293b; padding: 20px; border-radius: 10px; display: flex; flex-direction: column; gap: 15px;">
                <div style="display: flex; align-items: center; gap: 20px;">
                    <button id="playBtn" style="background: #3b82f6; border: none; color: white; padding: 10px 25px; border-radius: 8px; font-weight: bold; cursor: pointer; min-width: 100px;">PLAY</button>
                    <input type="range" id="seekBar" value="0" step="0.1" style="flex: 1; cursor: pointer;">
                    <span id="timeDisplay" style="color: white; font-family: monospace; font-size: 14px; min-width: 100px;">00:00 / 00:00</span>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: center; align-items: center;">
                    <button id="back5" style="background: #475569; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer;">-5s</button>
                    <button id="fwd5" style="background: #475569; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer;">+5s</button>
                    <span style="font-size: 12px; color: #94a3b8; margin-left:15px;">Speed:</span>
                    <select id="playbackRate" style="background: #475569; color: white; border: none; padding: 5px 10px; border-radius: 5px;">
                        <option value="0.5">0.5x</option>
                        <option value="1" selected>1.0x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2.0x</option>
                    </select>
                </div>
            </div>
        </div>

        <script>
            const v1 = document.getElementById('v1');
            const v2 = document.getElementById('v2');
            const playBtn = document.getElementById('playBtn');
            const seekBar = document.getElementById('seekBar');
            const timeDisplay = document.getElementById('timeDisplay');
            const mute1 = document.getElementById('mute1');
            const mute2 = document.getElementById('mute2');
            const vol1 = document.getElementById('vol1');
            const vol2 = document.getElementById('vol2');
            const volLab1 = document.getElementById('volLab1');
            const volLab2 = document.getElementById('volLab2');
            const back5 = document.getElementById('back5');
            const fwd5 = document.getElementById('fwd5');
            const rate = document.getElementById('playbackRate');

            let maxDuration = 0;

            const updateMetrics = () => {{
                const d1 = v1.duration || 0;
                const d2 = v2.duration || 0;
                maxDuration = Math.max(d1, d2);
            }};

            v1.onloadedmetadata = updateMetrics;
            v2.onloadedmetadata = updateMetrics;

            const togglePlay = () => {{
                if (v1.paused && v2.paused) {{
                    v1.play();
                    v2.play();
                    playBtn.textContent = 'PAUSE';
                    playBtn.style.background = '#ef4444';
                }} else {{
                    v1.pause();
                    v2.pause();
                    playBtn.textContent = 'PLAY';
                    playBtn.style.background = '#3b82f6';
                }}
            }};

            // Synchronize Play/Pause
            playBtn.addEventListener('click', togglePlay);

            // Keyboard Listeners
            document.addEventListener('keydown', (e) => {{
                if (e.code === 'Space') {{
                    e.preventDefault();
                    togglePlay();
                }} else if (e.code === 'ArrowRight') {{
                    e.preventDefault();
                    const target = Math.min(maxDuration, Math.max(v1.currentTime, v2.currentTime) + 3);
                    v1.currentTime = Math.min(target, v1.duration || target);
                    v2.currentTime = Math.min(target, v2.duration || target);
                }} else if (e.code === 'ArrowLeft') {{
                    e.preventDefault();
                    const target = Math.max(0, Math.max(v1.currentTime, v2.currentTime) - 3);
                    v1.currentTime = Math.min(target, v1.duration || target);
                    v2.currentTime = Math.min(target, v2.duration || target);
                }}
            }});

            // Synchronize Seeking
            seekBar.addEventListener('input', () => {{
                const targetTime = maxDuration * (seekBar.value / 100);
                v1.currentTime = Math.min(targetTime, v1.duration || targetTime);
                v2.currentTime = Math.min(targetTime, v2.duration || targetTime);
            }});

            // Volume Controls
            vol1.addEventListener('input', () => {{
                v1.volume = vol1.value;
                volLab1.textContent = Math.round(vol1.value * 100) + '%';
            }});
            vol2.addEventListener('input', () => {{
                v2.volume = vol2.value;
                volLab2.textContent = Math.round(vol2.value * 100) + '%';
            }});

            // Update Seek Bar & Time Display
            const syncUI = () => {{
                const currentTime = Math.max(v1.currentTime, v2.currentTime);
                
                if (maxDuration > 0) {{
                    const value = (100 / maxDuration) * currentTime;
                    seekBar.value = value;
                }}
                
                const curMins = Math.floor(currentTime / 60);
                const curSecs = Math.floor(currentTime % 60);
                const durMins = Math.floor(maxDuration / 60);
                const durSecs = Math.floor(maxDuration % 60);
                
                timeDisplay.textContent = 
                    `${{curMins.toString().padStart(2, '0')}}:${{curSecs.toString().padStart(2, '0')}} / ` +
                    `${{durMins.toString().padStart(2, '0')}}:${{durSecs.toString().padStart(2, '0')}}`;
                
                if (!v1.paused && !v2.paused && !v1.ended && !v2.ended) {{
                    if (Math.abs(v1.currentTime - v2.currentTime) > 0.3) {{
                        v2.currentTime = v1.currentTime;
                    }}
                }}
            }};

            v1.addEventListener('timeupdate', syncUI);
            v2.addEventListener('timeupdate', syncUI);

            // Individual Mute
            mute1.addEventListener('click', () => {{
                v1.muted = !v1.muted;
                mute1.textContent = v1.muted ? 'Unmute' : 'Mute';
                mute1.style.background = v1.muted ? '#475569' : '#e94560';
            }});

            mute2.addEventListener('click', () => {{
                v2.muted = !v2.muted;
                mute2.textContent = v2.muted ? 'Unmute' : 'Mute';
                mute2.style.background = v2.muted ? '#475569' : '#e94560';
            }});

            // Back/Forward
            back5.addEventListener('click', () => {{
                const target = Math.max(0, Math.max(v1.currentTime, v2.currentTime) - 5);
                v1.currentTime = Math.min(target, v1.duration || target);
                v2.currentTime = Math.min(target, v2.duration || target);
            }});
            fwd5.addEventListener('click', () => {{
                const target = Math.max(v1.currentTime, v2.currentTime) + 5;
                v1.currentTime = Math.min(target, v1.duration || target);
                v2.currentTime = Math.min(target, v2.duration || target);
            }});

            // Rate Change
            rate.addEventListener('change', () => {{
                v1.playbackRate = parseFloat(rate.value);
                v2.playbackRate = parseFloat(rate.value);
            }});
        </script>
        """
        st.components.v1.html(html_code, height=800)
        
    else:
        st.error(f"Missing one or both files for Candidate {cand_id}")
        st.write(f"Expected:")
        st.write(f"- {v1_full_path}")
        st.write(f"- {v2_full_path}")
else:
    st.info("👈 Enter a Candidate ID in the sidebar to begin review.")

st.sidebar.divider()
st.sidebar.markdown("### Status")
st.sidebar.write(f"Streaming from: `{st.session_state.base_path}`")
st.sidebar.write(f"Streaming Port: `{st.session_state.port}`")
