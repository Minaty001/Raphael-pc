// ── RaphaelApp UI logic ───────────────────────────────────────────────────────
// Backend communication (normalizeWsUrl, WebSocket connect/send, /health, /tts)
// lives in src/services/api.js and is exposed as window.RaphaelApi (loaded
// before this file). This module only renders and wires the UI to it.

const COLORS = {
    void: '#060912',
    surface: '#0E1424',
    elevated: '#1F2C4D',
    rimuru: '#3FA9F5',
    halo: '#A8E0FF',
    divine: '#F5C542',
    textMain: '#E8F1FA',
    muted: '#6B7C93',
    alert: '#FF6B8A'
};

const STATES = {
    IDLE: 'IDLE',
    LISTENING: 'LISTENING',
    THINKING: 'THINKING',
    SPEAKING: 'SPEAKING',
    ERROR: 'ERROR',
    WAKING: 'WAKING'
};

class RaphaelApp {
    constructor() {
        this.state = STATES.WAKING;
        this.ws = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.currentAudioSource = null;
        this.isAudioPlaying = false;
        
        // Speech Recognition setup
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            
            this.recognition.onstart = () => {
                this.setState(STATES.LISTENING);
                this.micBtn.classList.add('active');
            };
            
            this.recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                this.textInput.value = text;
                this.sendMessage(text);
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error', event.error);
                this.setState(STATES.IDLE);
                this.micBtn.classList.remove('active');
            };
            
            this.recognition.onend = () => {
                if (this.state === STATES.LISTENING) {
                    this.setState(STATES.IDLE);
                }
                this.micBtn.classList.remove('active');
            };
        } else {
            console.warn("SpeechRecognition not supported in this browser.");
        }

        this.initDOM();
        this.initCanvas();
        this.initParticles();
        this.loadSettings();
        this.bindEvents();
        this.wakeUp();
    }

    initDOM() {
        this.canvas = document.getElementById('halo-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.statusLabel = document.getElementById('status-label');
        this.responseText = document.getElementById('response-text');
        this.chatForm = document.getElementById('chat-form');
        this.textInput = document.getElementById('text-input');
        this.micBtn = document.getElementById('mic-btn');
        this.settingsBtn = document.getElementById('settings-btn');
        this.settingsPanel = document.getElementById('settings-panel');
        this.serverUrlInput = document.getElementById('server-url');
        this.saveSettingsBtn = document.getElementById('save-settings');
        this.closeSettingsBtn = document.getElementById('close-settings');
    }

    initCanvas() {
        // High DPI canvas
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        this.canvasWidth = rect.width;
        this.canvasHeight = rect.height;
        this.centerX = this.canvasWidth / 2;
        this.centerY = this.canvasHeight / 2;
        this.time = 0;
        
        requestAnimationFrame(this.renderCanvas.bind(this));
    }

    initParticles() {
        const particlesContainer = document.getElementById('particles');
        const canvas = document.createElement('canvas');
        particlesContainer.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        
        let width, height;
        const particles = [];
        
        const resize = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        };
        
        window.addEventListener('resize', resize);
        resize();
        
        for (let i = 0; i < 50; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                r: Math.random() * 1.5 + 0.5,
                vx: (Math.random() - 0.5) * 0.2,
                vy: (Math.random() - 0.5) * 0.2
            });
        }
        
        const render = () => {
            ctx.clearRect(0, 0, width, height);
            ctx.fillStyle = COLORS.rimuru;
            
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                
                if (p.x < 0) p.x = width;
                if (p.x > width) p.x = 0;
                if (p.y < 0) p.y = height;
                if (p.y > height) p.y = 0;
                
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
            });
            
            requestAnimationFrame(render);
        };
        
        render();
    }

    loadSettings() {
        const defaultWsUrl = RaphaelApi.defaultWsUrl();

        const stored   = localStorage.getItem('serverUrl');
        const resolved = stored ? (normalizeWsUrl(stored) || defaultWsUrl) : defaultWsUrl;

        this.serverUrl             = resolved;
        this.serverUrlInput.value  = resolved;

    }

    saveSettings() {
        const raw       = this.serverUrlInput.value;
        const defaultWsUrl = RaphaelApi.defaultWsUrl();
        const sanitized = normalizeWsUrl(raw) || defaultWsUrl;

        if (sanitized !== raw) {
            console.warn('[settings] Normalized serverUrl on save:', raw, '→', sanitized);
            this.serverUrlInput.value = sanitized;   // reflect corrected value in UI
        }

        this.serverUrl = sanitized;
        localStorage.setItem('serverUrl', sanitized); // always write the clean value

        this.settingsPanel.classList.add('hidden');
        this.connectWebSocket();
    }

    bindEvents() {
        this.settingsBtn.addEventListener('click', () => {
            this.settingsPanel.classList.remove('hidden');
        });
        
        this.closeSettingsBtn.addEventListener('click', () => {
            this.settingsPanel.classList.add('hidden');
        });
        
        this.saveSettingsBtn.addEventListener('click', () => {
            this.saveSettings();
        });

        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = this.textInput.value.trim();
            if (text) {
                this.sendMessage(text);
                this.textInput.value = '';
            }
        });

        this.micBtn.addEventListener('click', () => this.toggleListening());
        this.canvas.addEventListener('click', () => this.toggleListening());

        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.textInput && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                this.toggleListening();
            }
        });
    }

    toggleListening() {
        if (this.state === STATES.SPEAKING) {
            this.stopAudio();
            this.setState(STATES.IDLE);
            if (this.recognition) {
                try { this.recognition.start(); } catch(e) {}
            }
            return;
        }

        if (this.state === STATES.LISTENING) {
            if (this.recognition) this.recognition.stop();
            this.setState(STATES.IDLE);
        } else {
            if (this.recognition) {
                try { 
                    this.recognition.start(); 
                } catch(e) {
                    console.error("Recognition already started or error", e);
                }
            } else {
                alert("Speech recognition not supported");
            }
        }
    }

    async wakeUp() {
        // Always attempt the WebSocket: it does not require CORS, so chat works
        // even before RAPHAEL_ORIGIN is configured on the backend. /health is
        // used only to pick the initial state (it may be CORS-blocked or slow
        // during a Render cold start).
        this.connectWebSocket();
        try {
            const res = await RaphaelApi.health();
            if (res.ok) {
                this.setState(STATES.IDLE);
            } else {
                this.setState(STATES.ERROR);
            }
        } catch (e) {
            console.error("Wake health check failed", e);
            if (this.state === STATES.WAKING) {
                this.setState(STATES.ERROR);
            }
        }
    }

    connectWebSocket() {
        if (this.ws) {
            this.ws.onclose = null;
            this.ws.onerror = null;
            try {
                this.ws.close();
            } catch (e) {}
        }

        // RaphaelApi.connect is async now (it bootstraps the auth token).
        RaphaelApi.connect(this.serverUrl, {
            onopen: () => {
                console.log('WebSocket connected');
                if (this.state === STATES.WAKING || this.state === STATES.ERROR) {
                    this.setState(STATES.IDLE);
                }
            },

            onmessage: async (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'error' || data.error) {
                    const msg = data.error || data.message || 'Error';
                    console.error('WS Error:', msg);
                    this.setState(STATES.ERROR);
                    this.responseText.innerText = `Error: ${msg}`;
                    setTimeout(() => this.setState(STATES.IDLE), 3000);
                    return;
                }

                this.handleResponse(data);
            },

            onclose: () => {
                console.log('WebSocket disconnected');
                if (this.state !== STATES.WAKING) {
                    this.setState(STATES.ERROR);
                    setTimeout(() => this.connectWebSocket(), 3000);
                }
            },

            onerror: (err) => {
                console.error('WebSocket error:', err);
            }
        }).then((ws) => { this.ws = ws; });

        // Note: this.ws is set asynchronously; sendMessage guards readyState.
    }

    sendMessage(text) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        this.setState(STATES.THINKING);
        this.responseText.innerText = '';

        // Clear any existing action list
        const existingActions = document.getElementById('actions-container');
        if (existingActions) {
            existingActions.remove();
        }
        
        RaphaelApi.send(this.ws, {
            type: 'user.message',
            text: text
        });
    }

    async handleResponse(data) {
        // The Raphael gateway broadcasts event-bus events with shape
        // { type: <event_type>, ...payload }. Translate the ones the UI cares
        // about into the halo/response/action surfaces.
        const type = data.type;

        if (type === 'assistant.response') {
            // data.text holds the assistant's reply.
            const text = data.text || '';
            this.responseText.innerText = text;
            if (text) {
                this.setState(STATES.SPEAKING);
                await this.playTTS(text);
            } else {
                this.setState(STATES.IDLE);
            }
            return;
        }

        if (type === 'assistant.state') {
            // data.state is one of idle|listening|thinking|executing|speaking|error|offline
            const map = {
                idle: STATES.IDLE,
                listening: STATES.LISTENING,
                thinking: STATES.THINKING,
                executing: STATES.THINKING,
                speaking: STATES.SPEAKING,
                error: STATES.ERROR,
                offline: STATES.ERROR,
            };
            const next = map[data.state] || STATES.IDLE;
            if (this.state !== STATES.SPEAKING) this.setState(next);
            return;
        }

        if (type === 'tool.started' || type === 'tool.completed') {
            this.renderAction(data);
            return;
        }

        // Fallback: support the legacy {display, actions, speak} shape too.
        if (data.display) {
            this.responseText.innerText = data.display;
        }
        if (data.actions && Array.isArray(data.actions) && data.actions.length > 0) {
            data.actions.forEach((a) => this.renderAction({ tool: a.tool, args: a.args, status: 'success' }));
        }
        if (data.speak) {
            this.setState(STATES.SPEAKING);
            await this.playTTS(data.speak);
        } else if (!type) {
            this.setState(STATES.IDLE);
        }
    }

    /** Render a single tool event as an action badge in the response area. */
    renderAction(action) {
        let container = document.getElementById('actions-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'actions-container';
            container.className = 'actions-list';
            this.responseText.parentNode.appendChild(container);
        }

        const item = document.createElement('div');
        item.className = 'action-item';

        let badge = action.status === 'success' ? 'DONE' : (action.status || 'RUN');
        const tool = action.tool || 'tool';
        let desc = `${tool}`;
        if (action.args && Object.keys(action.args).length > 0) {
            desc += ` (${JSON.stringify(action.args)})`;
        }

        if (tool === 'open_url' && action.args && action.args.url) {
            badge = 'OPENED';
            try { window.open(action.args.url, '_blank'); } catch (e) {}
        }

        item.innerHTML = `
            <span class="action-badge">${badge}</span>
            <span class="action-desc">${desc}</span>
        `;
        container.appendChild(item);
    }

    async playTTS(text) {
        try {
            const arrayBuffer = await RaphaelApi.tts(text);
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            this.stopAudio(); // Stop any currently playing audio
            
            this.currentAudioSource = this.audioContext.createBufferSource();
            this.currentAudioSource.buffer = audioBuffer;
            this.currentAudioSource.connect(this.audioContext.destination);
            
            this.currentAudioSource.onended = () => {
                this.isAudioPlaying = false;
                if (this.state === STATES.SPEAKING) {
                    this.setState(STATES.IDLE);
                }
            };
            
            this.isAudioPlaying = true;
            this.currentAudioSource.start();
            
        } catch (e) {
            console.error('TTS playback error', e);
            this.setState(STATES.IDLE);
        }
    }
    
    stopAudio() {
        if (this.currentAudioSource && this.isAudioPlaying) {
            try {
                this.currentAudioSource.stop();
            } catch (e) { }
            this.isAudioPlaying = false;
        }
    }

    setState(newState) {
        this.state = newState;
        this.statusLabel.innerText = newState;
        
        switch(newState) {
            case STATES.IDLE:
                this.statusLabel.style.color = COLORS.rimuru;
                break;
            case STATES.LISTENING:
                this.statusLabel.style.color = COLORS.halo;
                break;
            case STATES.THINKING:
                this.statusLabel.style.color = COLORS.divine;
                break;
            case STATES.SPEAKING:
                this.statusLabel.style.color = COLORS.halo;
                break;
            case STATES.ERROR:
                this.statusLabel.style.color = COLORS.alert;
                break;
            case STATES.WAKING:
                this.statusLabel.style.color = COLORS.divine;
                break;
        }
    }

    renderCanvas() {
        this.time += 0.016; // ~60fps
        const ctx = this.ctx;
        const cx = this.centerX;
        const cy = this.centerY;
        const radius = 100;

        ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);

        // Common glow styles
        ctx.shadowBlur = 20;
        ctx.lineJoin = 'round';
        ctx.lineCap = 'round';

        let mainColor, coreGlowColor, rotationSpeed;

        switch (this.state) {
            case STATES.IDLE:
                mainColor = COLORS.rimuru;
                coreGlowColor = `${COLORS.rimuru}40`; // hex opacity
                rotationSpeed = 0.5;
                this.drawHalo(ctx, cx, cy, radius, mainColor, this.time * rotationSpeed, 1);
                this.drawSigil(ctx, cx, cy, radius * 0.6, mainColor, -this.time * 0.3);
                break;
                
            case STATES.LISTENING:
                mainColor = COLORS.halo;
                coreGlowColor = `${COLORS.halo}80`;
                const amplitude = Math.sin(this.time * 5) * 0.5 + 0.5;
                
                // Audio lines radiating
                ctx.strokeStyle = COLORS.halo;
                ctx.lineWidth = 2;
                ctx.shadowColor = COLORS.halo;
                for (let i = 0; i < 24; i++) {
                    const angle = (i / 24) * Math.PI * 2 + this.time * 0.2;
                    const rAmp = radius + 20 + amplitude * 30 * Math.random();
                    ctx.beginPath();
                    ctx.moveTo(cx + Math.cos(angle) * (radius + 5), cy + Math.sin(angle) * (radius + 5));
                    ctx.lineTo(cx + Math.cos(angle) * rAmp, cy + Math.sin(angle) * rAmp);
                    ctx.stroke();
                }
                
                this.drawHalo(ctx, cx, cy, radius, mainColor, this.time, 1.5 + amplitude * 0.5);
                this.drawSigil(ctx, cx, cy, radius * 0.6, mainColor, -this.time * 0.5);
                break;
                
            case STATES.THINKING:
                mainColor = COLORS.divine;
                coreGlowColor = `${COLORS.divine}60`;
                
                // Fragmented arcs
                ctx.strokeStyle = mainColor;
                ctx.shadowColor = mainColor;
                ctx.lineWidth = 4;
                for (let i = 0; i < 6; i++) {
                    const angle = (i / 6) * Math.PI * 2 + this.time * 2;
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius, angle, angle + Math.PI / 4);
                    ctx.stroke();
                    
                    const angle2 = (i / 6) * Math.PI * 2 - this.time * 1.5;
                    ctx.beginPath();
                    ctx.arc(cx, cy, radius + 15, angle2, angle2 + Math.PI / 6);
                    ctx.stroke();
                }
                
                this.drawSigil(ctx, cx, cy, radius * 0.6, mainColor, this.time);
                break;
                
            case STATES.SPEAKING:
                mainColor = COLORS.halo;
                coreGlowColor = `${COLORS.halo}80`;
                const speakPulse = Math.sin(this.time * 8) * 0.5 + 0.5;
                
                // Expanding rings
                ctx.strokeStyle = mainColor;
                ctx.shadowColor = mainColor;
                for (let i = 0; i < 3; i++) {
                    const ringTime = (this.time * 2 + i * 2) % 6;
                    if (ringTime < 3) {
                        ctx.globalAlpha = 1 - (ringTime / 3);
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.arc(cx, cy, radius + ringTime * 20, 0, Math.PI * 2);
                        ctx.stroke();
                    }
                }
                ctx.globalAlpha = 1;
                
                this.drawHalo(ctx, cx, cy, radius, mainColor, this.time * 1.5, 2 + speakPulse);
                this.drawSigil(ctx, cx, cy, radius * 0.6, mainColor, -this.time);
                break;
                
            case STATES.ERROR:
                mainColor = COLORS.alert;
                coreGlowColor = `${COLORS.alert}40`;
                this.drawHalo(ctx, cx, cy, radius, mainColor, this.time * 0.1, 1);
                ctx.font = '24px JetBrains Mono';
                ctx.fillStyle = mainColor;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('ERR', cx, cy);
                break;
                
            case STATES.WAKING:
                mainColor = COLORS.divine;
                coreGlowColor = `${COLORS.divine}40`;
                this.drawHalo(ctx, cx, cy, radius, mainColor, this.time * 3, 1.5);
                this.drawSigil(ctx, cx, cy, radius * 0.4, mainColor, -this.time * 2);
                break;
        }

        // Core radial glow
        ctx.shadowBlur = 0; // Turn off shadow for gradient
        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        gradient.addColorStop(0, coreGlowColor);
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();

        requestAnimationFrame(this.renderCanvas.bind(this));
    }

    drawHalo(ctx, cx, cy, radius, color, rotation, thicknessMulti) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(rotation);
        
        ctx.strokeStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 15;
        
        // Base ring
        ctx.lineWidth = 2 * thicknessMulti;
        ctx.beginPath();
        ctx.arc(0, 0, radius, 0, Math.PI * 2);
        ctx.stroke();
        
        // Outer accent ring
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(0, 0, radius + 8, 0, Math.PI * 2);
        ctx.stroke();
        
        // Arc segments
        ctx.lineWidth = 4 * thicknessMulti;
        for (let i = 0; i < 4; i++) {
            ctx.beginPath();
            ctx.arc(0, 0, radius, (i * Math.PI / 2), (i * Math.PI / 2) + Math.PI / 4);
            ctx.stroke();
        }
        
        ctx.restore();
    }

    drawSigil(ctx, cx, cy, radius, color, rotation) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(rotation);
        
        ctx.strokeStyle = color;
        ctx.shadowColor = color;
        ctx.shadowBlur = 10;
        ctx.lineWidth = 2;
        
        // Hexagon
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2;
            if (i === 0) ctx.moveTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
            else ctx.lineTo(Math.cos(angle) * radius, Math.sin(angle) * radius);
        }
        ctx.closePath();
        ctx.stroke();
        
        // Inner geometry (Triangle)
        ctx.beginPath();
        for (let i = 0; i < 3; i++) {
            const angle = (i / 3) * Math.PI * 2 + Math.PI / 6;
            if (i === 0) ctx.moveTo(Math.cos(angle) * radius * 0.7, Math.sin(angle) * radius * 0.7);
            else ctx.lineTo(Math.cos(angle) * radius * 0.7, Math.sin(angle) * radius * 0.7);
        }
        ctx.closePath();
        ctx.stroke();
        
        ctx.restore();
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RaphaelApp();
});
