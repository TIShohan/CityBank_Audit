import streamlit as st
import os
import threading
import socketserver
import http.server
import socket
import base64

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
BASE_PATH = r"D:\City Bank_Downloads"

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Adds support for Range requests (required for video seeking)."""
    def __init__(self, *args, **kwargs):
        self.base_dir = kwargs.pop('base_dir', BASE_PATH)
        super().__init__(*args, **kwargs)

    def translate_path(self, path):
        # Ensure we serve files from BASE_PATH regardless of current working directory
        path = super().translate_path(path)
        rel_path = os.path.relpath(path, os.getcwd())
        return os.path.join(self.base_dir, rel_path)

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

def start_server(port, base_path):
    def handler_factory(*args, **kwargs):
        return RangeRequestHandler(*args, base_dir=base_path, **kwargs)
    
    with socketserver.TCPServer(("", port), handler_factory) as httpd:
        httpd.serve_forever()

if 'port' not in st.session_state:
    port = find_free_port()
    st.session_state.port = port
    thread = threading.Thread(target=start_server, args=(port, BASE_PATH), daemon=True)
    thread.start()

# --- UI ---
st.markdown('<h1 class="title-text">🎥 Side-by-Side Video Reviewer</h1>', unsafe_allow_html=True)

cand_id = st.text_input("Enter Candidate ID (e.g., 794)", help="The folder name in D:\City Bank_Downloads")

if cand_id:
    # URL construction
    v1_rel_path = f"{cand_id}/{cand_id}_screenrecord.mp4"
    v2_rel_path = f"{cand_id}/{cand_id}_webcam.mp4"
    
    v1_full_path = os.path.join(BASE_PATH, v1_rel_path)
    v2_full_path = os.path.join(BASE_PATH, v2_rel_path)
    
    if os.path.exists(v1_full_path) and os.path.exists(v2_full_path):
        v1_url = f"http://localhost:{st.session_state.port}/{v1_rel_path}"
        v2_url = f"http://localhost:{st.session_state.port}/{v2_rel_path}"
        
        # Synchronized Player HTML/JS
        html_code = f"""
        <div id="wrapper" style="display: flex; flex-direction: column; align-items: center; gap: 20px; background: #0f172a; padding: 20px; border-radius: 15px;">
            <div style="display: flex; gap: 15px; width: 100%; justify-content: center;">
                <div style="flex: 1; position: relative; border: 2px solid #334155; border-radius: 10px; overflow: hidden;">
                    <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; z-index: 10;">SCREEN RECORD</div>
                    <video id="v1" width="100%" style="background: black;">
                        <source src="{v1_url}" type="video/mp4">
                    </video>
                    <div style="padding: 10px; background: #1e293b; display: flex; justify-content: space-between; align-items: center;">
                        <button id="mute1" style="background: #e94560; border: none; color: white; padding: 5px 15px; border-radius: 5px; cursor: pointer;">Mute Screen</button>
                    </div>
                </div>
                
                <div style="flex: 1; position: relative; border: 2px solid #334155; border-radius: 10px; overflow: hidden;">
                    <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; z-index: 10;">WEBCAM RECORD</div>
                    <video id="v2" width="100%" style="background: black;">
                        <source src="{v2_url}" type="video/mp4">
                    </video>
                    <div style="padding: 10px; background: #1e293b; display: flex; justify-content: space-between; align-items: center;">
                        <button id="mute2" style="background: #e94560; border: none; color: white; padding: 5px 15px; border-radius: 5px; cursor: pointer;">Mute Webcam</button>
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
                
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="back5" style="background: #475569; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer;">-5s</button>
                    <button id="fwd5" style="background: #475569; border: none; color: white; padding: 5px 12px; border-radius: 5px; cursor: pointer;">+5s</button>
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
            const back5 = document.getElementById('back5');
            const fwd5 = document.getElementById('fwd5');
            const rate = document.getElementById('playbackRate');

            // Synchronize Play/Pause
            playBtn.addEventListener('click', () => {{
                if (v1.paused) {{
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
            }});

            // Synchronize Seeking
            seekBar.addEventListener('input', () => {{
                const time = v1.duration * (seekBar.value / 100);
                v1.currentTime = time;
                v2.currentTime = time;
            }});

            // Update Seek Bar & Time Display
            v1.addEventListener('timeupdate', () => {{
                const value = (100 / v1.duration) * v1.currentTime;
                seekBar.value = value;
                
                // Format time
                const curMins = Math.floor(v1.currentTime / 60);
                const curSecs = Math.floor(v1.currentTime % 60);
                const durMins = Math.floor(v1.duration / 60);
                const durSecs = Math.floor(v1.duration % 60);
                
                timeDisplay.textContent = 
                    `${{curMins.toString().padStart(2, '0')}}:${{curSecs.toString().padStart(2, '0')}} / ` +
                    `${{durMins.toString().padStart(2, '0')}}:${{durSecs.toString().padStart(2, '0')}}`;
                
                // Sync check (prevent drift)
                if (Math.abs(v1.currentTime - v2.currentTime) > 0.3) {{
                    v2.currentTime = v1.currentTime;
                }}
            }});

            // Individual Mute
            mute1.addEventListener('click', () => {{
                v1.muted = !v1.muted;
                mute1.textContent = v1.muted ? 'Unmute Screen' : 'Mute Screen';
                mute1.style.background = v1.muted ? '#475569' : '#e94560';
            }});

            mute2.addEventListener('click', () => {{
                v2.muted = !v2.muted;
                mute2.textContent = v2.muted ? 'Unmute Webcam' : 'Mute Webcam';
                mute2.style.background = v2.muted ? '#475569' : '#e94560';
            }});

            // Back/Forward
            back5.addEventListener('click', () => {{
                v1.currentTime -= 5;
                v2.currentTime = v1.currentTime;
            }});
            fwd5.addEventListener('click', () => {{
                v1.currentTime += 5;
                v2.currentTime = v1.currentTime;
            }});

            // Rate Change
            rate.addEventListener('change', () => {{
                v1.playbackRate = parseFloat(rate.value);
                v2.playbackRate = parseFloat(rate.value);
            }});

            // Ensure durations are loaded for seeker
            v1.onloadedmetadata = () => {{
                seekBar.max = 100;
            }};
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
st.sidebar.write(f"Serving files from: `{BASE_PATH}`")
st.sidebar.write(f"Streaming Port: `{st.session_state.port}`")
