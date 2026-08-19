// ── RaphaelApp HUD logic ─────────────────────────────────────────────────────
// Backend communication (normalizeWsUrl, WebSocket connect/send, /health,
// /status, REST helpers) lives in src/services/api.js and is exposed as
// window.RaphaelApi (loaded before this file). This module only renders and
// wires the desktop HUD to real runtime data.

const COLORS = {
    void: '#060912', surface: '#0E1424', elevated: '#1F2C4D',
    rimuru: '#3FA9F5', halo: '#A8E0FF', divine: '#F5C542',
    ok: '#4ADE80', textMain: '#E8F1FA', muted: '#6B7C93', alert: '#FF6B8A'
};

// The 15 real brain states from raphael.core.state_manager.AssistantState
const STATES = {
    IDLE: 'IDLE', OBSERVING: 'OBSERVING', LISTENING: 'LISTENING',
    UNDERSTANDING: 'UNDERSTANDING', RETRIEVING_MEMORY: 'RETRIEVING_MEMORY',
    THINKING: 'THINKING', PLANNING: 'PLANNING', ASKING: 'ASKING',
    EXECUTING: 'EXECUTING', VERIFYING: 'VERIFYING', LEARNING: 'LEARNING',
    REFLECTING: 'REFLECTING', SPEAKING: 'SPEAKING', ERROR: 'ERROR', OFFLINE: 'OFFLINE'
};

class RaphaelApp {
    constructor() {
        this.state = STATES.OFFLINE;
        this.ws = null;
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        this.currentAudioSource = null;
        this.isAudioPlaying = false;
        this._actionItems = {};
        this._latencySent = 0;
        this._pendingConfirm = null;

        // a11y / perf flags
        this.reducedMotion = !!(window.matchMedia &&
            window.matchMedia('(prefers-reduced-motion: reduce)').matches);
        this.canvasRunning = false;
        this.particlesRunning = false;

        // Speech recognition (optional, where supported)
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';
            this.recognition.onstart = () => { this.setState(STATES.LISTENING); this.micBtn.classList.add('active'); };
            this.recognition.onresult = (e) => { const t = e.results[0][0].transcript; this.textInput.value = t; this.sendMessage(t); };
            this.recognition.onerror = () => { this.setState(STATES.IDLE); this.micBtn.classList.remove('active'); };
            this.recognition.onend = () => { if (this.state === STATES.LISTENING) this.setState(STATES.IDLE); this.micBtn.classList.remove('active'); };
        }

        this.initDOM();
        this.initCanvas();
        this.initParticles();
        this.loadSettings();
        this.bindEvents();
        document.addEventListener('visibilitychange', () => this.onVisibility());
        this.startClock();

        if (!this.reducedMotion) {
            this.canvasRunning = true;
            requestAnimationFrame(this.renderCanvas.bind(this));
        } else {
            this.renderCanvas(true);
        }

        this.wakeUp();
    }

    initDOM() {
        this.canvas = document.getElementById('halo-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.statusLabel = document.getElementById('status-label');
        this.conversation = document.getElementById('conversation');
        this.chatForm = document.getElementById('chat-form');
        this.textInput = document.getElementById('text-input');
        this.micBtn = document.getElementById('mic-btn');
        this.sendBtn = document.getElementById('send-btn');
        this.settingsBtn = document.getElementById('settings-btn');
        this.settingsPanel = document.getElementById('settings-panel');
        this.serverUrlInput = document.getElementById('server-url');
        this.saveSettingsBtn = document.getElementById('save-settings');
        this.closeSettingsBtn = document.getElementById('close-settings');
        this.statePill = document.getElementById('state-pill');
        this.statePillText = document.getElementById('state-pill-text');
        this.connStatus = document.getElementById('conn-status');
        this.wsLatency = document.getElementById('ws-latency');
        this.sbState = document.getElementById('sb-state');
        this.runtimeMode = document.getElementById('runtime-mode');
        this.effectiveMode = document.getElementById('effective-mode');
        this.interruptBtn = document.getElementById('interrupt-btn');
        this.eventLog = document.getElementById('event-log');
        this.taskList = document.getElementById('task-list');
        this.memoryList = document.getElementById('memory-list');
        this.confirmPanel = document.getElementById('confirm-panel');
        this.confirmText = document.getElementById('confirm-text');
        this.confirmApprove = document.getElementById('confirm-approve');
        this.confirmDeny = document.getElementById('confirm-deny');
        this.toasts = document.getElementById('toasts');
    }

    // ── Canvas (single, guarded loop) ──────────────────────────
    initCanvas() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        const w = rect.width || 320, h = rect.height || 320;
        this.canvas.width = w * dpr;
        this.canvas.height = h * dpr;
        this.ctx.scale(dpr, dpr);
        this.canvasWidth = w; this.canvasHeight = h;
        this.centerX = w / 2; this.centerY = h / 2;
        this.time = 0;
        this.radiusScale = Math.min(w, h) / 320; // scale artwork to box

        window.addEventListener('resize', () => {
            const r = this.canvas.getBoundingClientRect();
            const w2 = r.width || 320, h2 = r.height || 320;
            this.canvas.width = w2 * dpr; this.canvas.height = h2 * dpr;
            this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            this.canvasWidth = w2; this.canvasHeight = h2;
            this.centerX = w2 / 2; this.centerY = h2 / 2;
            this.radiusScale = Math.min(w2, h2) / 320;
            if (this.reducedMotion) this.renderCanvas(true);
        });
    }

    initParticles() {
        const container = document.getElementById('particles');
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        let width, height;
        const particles = [];
        const dpr = window.devicePixelRatio || 1;

        const resize = () => {
            width = window.innerWidth; height = window.innerHeight;
            canvas.width = width * dpr; canvas.height = height * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        window.addEventListener('resize', resize);
        resize();

        for (let i = 0; i < 48; i++) {
            particles.push({
                x: Math.random() * width, y: Math.random() * height,
                r: Math.random() * 1.5 + 0.4,
                vx: (Math.random() - 0.5) * 0.18, vy: (Math.random() - 0.5) * 0.18
            });
        }

        const render = () => {
            if (this.reducedMotion || document.hidden) { this.particlesRunning = false; return; }
            this.particlesRunning = true;
            ctx.clearRect(0, 0, width, height);
            ctx.fillStyle = COLORS.rimuru;
            particles.forEach(p => {
                p.x += p.vx; p.y += p.vy;
                if (p.x < 0) p.x = width; if (p.x > width) p.x = 0;
                if (p.y < 0) p.y = height; if (p.y > height) p.y = 0;
                ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
            });
            requestAnimationFrame(render);
        };
        this._particleRender = render;
        if (!this.reducedMotion) requestAnimationFrame(render);
    }

    onVisibility() {
        if (document.hidden) return;
        if (!this.reducedMotion && !this.canvasRunning) { this.canvasRunning = true; requestAnimationFrame(this.renderCanvas.bind(this)); }
        if (!this.reducedMotion && !this.particlesRunning && this._particleRender) { this.particlesRunning = true; requestAnimationFrame(this._particleRender); }
    }

    startClock() {
        const tick = () => {
            const d = new Date();
            const el = document.getElementById('clock');
            if (el) el.textContent = d.toLocaleTimeString('en-GB');
        };
        tick(); setInterval(tick, 1000);
    }

    // ── Settings ──────────────────────────────────────────────
    loadSettings() {
        const defaultWsUrl = RaphaelApi.defaultWsUrl();
        const stored = localStorage.getItem('serverUrl');
        const resolved = stored ? (normalizeWsUrl(stored) || defaultWsUrl) : defaultWsUrl;
        this.serverUrl = resolved;
        this.serverUrlInput.value = resolved;
    }

    saveSettings() {
        const raw = this.serverUrlInput.value;
        const sanitized = normalizeWsUrl(raw) || RaphaelApi.defaultWsUrl();
        if (sanitized !== raw) { this.serverUrlInput.value = sanitized; }
        this.serverUrl = sanitized;
        localStorage.setItem('serverUrl', sanitized);
        this.settingsPanel.classList.add('hidden');
        this.connectWebSocket();
    }

    // ── Events ────────────────────────────────────────────────
    bindEvents() {
        this.settingsBtn.addEventListener('click', () => this.settingsPanel.classList.remove('hidden'));
        this.closeSettingsBtn.addEventListener('click', () => this.settingsPanel.classList.add('hidden'));
        this.saveSettingsBtn.addEventListener('click', () => this.saveSettings());

        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = this.textInput.value.trim();
            if (text) { this.sendMessage(text); this.textInput.value = ''; }
        });

        this.micBtn.addEventListener('click', () => this.toggleListening());
        this.canvas.addEventListener('click', () => this.toggleListening());
        window.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && document.activeElement !== this.textInput) {
                e.preventDefault(); this.toggleListening();
            }
        });

        // Tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
            });
        });

        // Runtime controls
        this.runtimeMode.addEventListener('change', async () => {
            try {
                await RaphaelApi.setMode(this.runtimeMode.value);
                this.toast('Runtime', `Mode → ${this.runtimeMode.value}`);
            } catch (e) { this.toast('Error', 'Could not set mode', true); }
        });
        this.interruptBtn.addEventListener('click', async () => {
            try { await RaphaelApi.interrupt(); this.toast('Runtime', 'Interrupted'); }
            catch (e) { this.toast('Error', 'Interrupt failed', true); }
        });

        // Confirmation modal
        this.confirmApprove.addEventListener('click', () => this.resolveConfirm(true));
        this.confirmDeny.addEventListener('click', () => this.resolveConfirm(false));
    }

    toggleListening() {
        if (this.state === STATES.SPEAKING && this.recognition) {
            this.stopAudio(); this.setState(STATES.IDLE);
            try { this.recognition.start(); } catch (e) {}
            return;
        }
        if (this.state === STATES.LISTENING) {
            if (this.recognition) this.recognition.stop();
            this.setState(STATES.IDLE);
        } else if (this.recognition) {
            try { this.recognition.start(); } catch (e) {}
        } else {
            this.toast('Voice', 'Speech recognition not supported in this browser', true);
        }
    }

    async wakeUp() {
        this.connectWebSocket();
        try {
            await RaphaelApi.status();
            this.setConn(true);
        } catch (e) {
            this.setConn(false);
            if (this.state === STATES.OFFLINE) this.setState(STATES.ERROR);
        }
        // Pull real datasets for the side panels.
        this.refreshTasks();
        this.refreshMemories();
        this.refreshStatus();
        // Keep tasks/memory fresh while connected.
        this._poll = setInterval(() => { this.refreshTasks(); this.refreshStatus(); }, 4000);
    }

    setConn(ok) {
        if (ok) {
            this.connStatus.textContent = '● connected';
            this.connStatus.className = 'conn-on';
        } else {
            this.connStatus.textContent = '● disconnected';
            this.connStatus.className = 'conn-off';
        }
    }

    connectWebSocket() {
        if (this.ws) { this.ws.onclose = null; this.ws.onerror = null; try { this.ws.close(); } catch (e) {} }
        this._latencySent = Date.now();
        RaphaelApi.connect(this.serverUrl, {
            onopen: () => {
                this.setConn(true);
                this.wsLatency.textContent = 'latency: --';
                if (this.state === STATES.OFFLINE || this.state === STATES.ERROR) this.setState(STATES.IDLE);
            },
            onmessage: async (event) => {
                // latency estimate for the sync frame
                const dt = Date.now() - this._latencySent;
                if (dt < 5000) this.wsLatency.textContent = `latency: ${dt}ms`;
                await this.handleResponse(JSON.parse(event.data));
            },
            onclose: () => {
                this.setConn(false);
                if (this.state !== STATES.OFFLINE) {
                    this.setState(STATES.ERROR);
                    setTimeout(() => this.connectWebSocket(), 3000);
                }
            },
            onerror: (err) => console.error('WebSocket error:', err)
        }).then((ws) => { this.ws = ws; });
    }

    sendMessage(text) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            this.toast('Offline', 'Not connected to runtime', true);
            return;
        }
        this.addMessage(text, 'user');
        this.setState(STATES.THINKING);
        this._actionItems = {};
        const existing = document.getElementById('actions-container');
        if (existing) existing.remove();
        RaphaelApi.send(this.ws, { type: 'user.message', text });
    }

    // ── Real event handling ───────────────────────────────────
    async handleResponse(data) {
        const type = data.type;

        if (type === 'error' || data.error) {
            const msg = data.error || data.message || 'Error';
            this.logEvent('error', msg);
            this.setState(STATES.ERROR);
            this.addMessage(msg, 'error');
            setTimeout(() => { if (this.state === STATES.ERROR) this.setState(STATES.IDLE); }, 3000);
            return;
        }

        if (type === 'pong') { this.wsLatency.textContent = `latency: ${(Date.now() - this._latencySent)}ms`; return; }
        if (type === 'ping') { RaphaelApi.send(this.ws, { type: 'pong', timestamp: Date.now() }); return; }

        if (type === 'assistant.state') {
            const newState = data.state || 'IDLE';
            if (this.state !== STATES.SPEAKING) this.setState(newState);
            this.logEvent('state', `${this.state} ← ${data.previous_state || ''}`);
            if (data.metrics) this.renderMetrics(data.metrics);
            if (data.metadata) this.renderRuntimeSummary(data.metadata);
            return;
        }

        if (type === 'assistant.message') {
            const text = data.text || '';
            this.addMessage(text, 'assistant');
            if (text && this.state === STATES.SPEAKING) { /* already speaking */ }
            return;
        }

        if (type === 'assistant.response') {
            const text = data.text || '';
            this.addMessage(text, 'assistant');
            if (text) { this.setState(STATES.SPEAKING); await this.playTTS(text); }
            else this.setState(STATES.IDLE);
            return;
        }

        if (type === 'plan.step.start') { this.logEvent('tool', `▸ ${data.step || data.description || 'step'} (${data.tool || ''})`); return; }
        if (type === 'plan.step.completed') { this.logEvent('tool', `✓ ${data.step || 'step'}`); return; }
        if (type === 'plan.step.failed') { this.logEvent('error', `✗ ${data.step || 'step'}`); return; }

        if (type === 'tool.started') {
            this.renderAction({ tool: data.tool, args: data.args, status: 'RUN' });
            this.logEvent('tool', `▶ ${data.tool || 'tool'} started`);
            return;
        }
        if (type === 'tool.completed') {
            this.renderAction({ tool: data.tool, args: data.args, status: data.status || 'success' });
            this.logEvent('tool', `✔ ${data.tool || 'tool'} done`);
            return;
        }

        if (type === 'security.confirmation_requested') {
            this.showConfirm(data);
            return;
        }

        if (type === 'notification.created') {
            this.toast(data.title || 'Notification', data.message || '');
            this.logEvent('state', `🔔 ${data.title || 'notification'}`);
            return;
        }

        if (type === 'reflection.completed') {
            this.logEvent('state', `🪞 ${data.summary || 'reflection complete'}`);
            return;
        }
        if (type === 'learning.lesson_created') {
            this.logEvent('state', `📚 ${data.lesson || 'learned'}`);
            return;
        }
        if (type === 'proactive.topic_generated' || type === 'curiosity.question_generated') {
            const t = data.topic || data.question || data.text || 'proactive';
            this.toast('Raphael wonders', t);
            this.logEvent('state', `💡 ${t}`);
            return;
        }
        if (type === 'routine.detected') {
            this.logEvent('state', `🔁 routine: ${data.name || 'detected'}`);
            return;
        }

        // Generic fallback for any other event the bus emits.
        this.logEvent('', type);
    }

    // ── Conversation + activity rendering ────────────────────
    addMessage(text, kind) {
        if (!text) return;
        const div = document.createElement('div');
        div.className = 'msg msg-' + kind;
        div.textContent = text; // textContent = no HTML injection
        this.conversation.appendChild(div);
        this.conversation.scrollTop = this.conversation.scrollHeight;
    }

    logEvent(kind, text) {
        const div = document.createElement('div');
        div.className = 'evt' + (kind ? ' evt-' + kind : '');
        const time = new Date().toLocaleTimeString('en-GB');
        const label = kind ? `<span class="evt-type">${kind.toUpperCase()}</span>` : '';
        div.innerHTML = `${label}<span class="evt-time">${time}</span> ${this._esc(text)}`;
        if (!kind) div.firstChild && (div.firstChild.textContent = '');
        this.eventLog.prepend(div);
        // cap log length
        while (this.eventLog.children.length > 60) this.eventLog.lastChild.remove();
    }

    _esc(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

    // ── Metrics ───────────────────────────────────────────────
    renderMetrics(m) {
        if (typeof m.cpu_percent === 'number') this.setMetric('cpu', m.cpu_percent, m.cpu_percent.toFixed(0) + '%');
        if (typeof m.ram_percent === 'number') {
            this.setMetric('ram', m.ram_percent, m.ram_percent.toFixed(0) + '%');
            this.setText('m-ram-sub', `${m.ram_used_mb ?? '--'} / ${m.ram_total_mb ?? '--'} MB`);
        }
        if (typeof m.disk_percent === 'number') {
            this.setMetric('disk', m.disk_percent, m.disk_percent.toFixed(0) + '%');
            this.setText('m-disk-sub', `${m.disk_used_gb ?? '--'} / ${m.disk_total_gb ?? '--'} GB`);
        }
        if (m.battery && m.battery.available) {
            document.getElementById('battery-wrap').hidden = false;
            this.setMetric('bat', m.battery.percent, m.battery.percent.toFixed(0) + '%');
        }
    }

    setMetric(key, pct, label) {
        const bar = document.getElementById('bar-' + key);
        if (bar) bar.style.width = Math.max(0, Math.min(100, pct)) + '%';
        const txt = document.getElementById('m-' + key);
        if (txt) txt.textContent = label;
    }
    setText(id, text) { const el = document.getElementById(id); if (el) el.textContent = text; }

    renderRuntimeSummary(meta) {
        if (!meta) return;
        this.setState(meta.current_state || this.state);
        this.setText('sb-state', 'state: ' + (meta.current_state || '--'));
    }

    // ── Tasks (REST) ──────────────────────────────────────────
    async refreshTasks() {
        try {
            const tasks = await RaphaelApi.listTasks();
            if (!Array.isArray(tasks)) return;
            if (tasks.length === 0) {
                this.taskList.innerHTML = '<div class="empty">No background tasks.</div>';
                return;
            }
            const statusClass = s => ({ 'running': 'running', 'paused': 'paused', 'done': 'done', 'failed': 'failed', 'pending': 'running' }[s] || 'running');
            this.taskList.innerHTML = tasks.map(t => `
                <div class="task" data-id="${t.id}">
                    <div class="task-head">
                        <span class="task-name">${this._esc(t.name || 'Task')}</span>
                        <span class="task-status ${statusClass(t.status)}">${this._esc(t.status || 'running')}</span>
                    </div>
                    <div class="task-meta">
                        <button class="task-btn" data-act="pause" data-id="${t.id}">Pause</button>
                        <button class="task-btn" data-act="resume" data-id="${t.id}">Resume</button>
                        <button class="task-btn" data-act="cancel" data-id="${t.id}">Cancel</button>
                    </div>
                </div>`).join('');
            this.taskList.querySelectorAll('.task-btn').forEach(b => {
                b.addEventListener('click', () => this.taskAction(b.dataset.act, b.dataset.id));
            });
        } catch (e) { /* auth/network — ignore silently, will retry on poll */ }
    }

    async taskAction(act, id) {
        try {
            await RaphaelApi.taskAction(act, id);
            this.refreshTasks();
        } catch (e) { this.toast('Error', 'Task action failed', true); }
    }

    // ── Memory (REST) ────────────────────────────────────────
    async refreshMemories() {
        try {
            const mems = await RaphaelApi.listMemories();
            if (!Array.isArray(mems) || mems.length === 0) {
                this.memoryList.innerHTML = '<div class="empty">No memories loaded.</div>';
                return;
            }
            this.memoryList.innerHTML = mems.slice(0, 40).map(m => `
                <div class="mem">
                    <div class="mem-type">${this._esc(m.type || m.kind || 'memory')}</div>
                    <div class="mem-text">${this._esc(m.content || m.text || JSON.stringify(m).slice(0, 160))}</div>
                </div>`).join('');
        } catch (e) { /* ignore */ }
    }

    // ── Status (REST) ────────────────────────────────────────
    async refreshStatus() {
        try {
            const s = await RaphaelApi.status();
            if (s.metrics) this.renderMetrics(s.metrics);
            if (s.effective_mode) { this.effectiveMode.textContent = s.effective_mode; }
        } catch (e) { /* ignore */ }
    }

    // ── Confirmation modal ───────────────────────────────────
    showConfirm(data) {
        this._pendingConfirm = data.request_id;
        this.confirmText.textContent = this._esc(data.message || data.tool || 'A tool requires approval.');
        this.confirmPanel.classList.remove('hidden');
    }
    resolveConfirm(approved) {
        if (this._pendingConfirm && this.ws) {
            RaphaelApi.send(this.ws, { type: 'security.confirm_response', request_id: this._pendingConfirm, approved });
        }
        this._pendingConfirm = null;
        this.confirmPanel.classList.add('hidden');
    }

    // ── Toasts ───────────────────────────────────────────────
    toast(title, body, alert) {
        const div = document.createElement('div');
        div.className = 'toast' + (alert ? ' toast-alert' : '');
        const t = document.createElement('div'); t.className = 'toast-title'; t.textContent = title;
        const b = document.createElement('div'); b.textContent = body || '';
        div.appendChild(t); div.appendChild(b);
        this.toasts.appendChild(div);
        setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 300); }, 5000);
    }

    // ── Action badges (tool events) ──────────────────────────
    renderAction(action) {
        const tool = action.tool || 'tool';
        const args = action.args && typeof action.args === 'object' ? action.args : {};
        let item = this._actionItems[tool];
        if (!item) {
            let container = document.getElementById('actions-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'actions-container';
                container.className = 'actions-list';
                this.conversation.parentNode.insertBefore(container, this.conversation.nextSibling);
            }
            item = document.createElement('div');
            item.className = 'action-item';
            container.appendChild(item);
            this._actionItems[tool] = item;
        }
        const status = action.status || 'RUN';
        const badgeText = status === 'success' ? 'DONE' : status === 'error' ? 'FAIL' : status === 'RUN' ? 'RUN' : status.toUpperCase();
        let desc = tool;
        const keys = Object.keys(args);
        if (keys.length) {
            const preview = keys.map(k => `${k}=${typeof args[k] === 'string' ? args[k] : JSON.stringify(args[k])}`).join(' ');
            desc += ` (${preview.length > 120 ? preview.slice(0, 117) + '…' : preview})`;
        }
        item.innerHTML = '';
        const badge = document.createElement('span'); badge.className = 'action-badge'; badge.textContent = badgeText;
        if (status === 'error') badge.className += ' action-badge--error';
        const descEl = document.createElement('span'); descEl.className = 'action-desc'; descEl.textContent = desc;
        item.appendChild(badge); item.appendChild(descEl);
    }

    // ── TTS ──────────────────────────────────────────────────
    async playTTS(text) {
        try {
            const arrayBuffer = await RaphaelApi.tts(text);
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            this.stopAudio();
            this.currentAudioSource = this.audioContext.createBufferSource();
            this.currentAudioSource.buffer = audioBuffer;
            this.currentAudioSource.connect(this.audioContext.destination);
            this.currentAudioSource.onended = () => { this.isAudioPlaying = false; if (this.state === STATES.SPEAKING) this.setState(STATES.IDLE); };
            this.isAudioPlaying = true;
            this.currentAudioSource.start();
        } catch (e) {
            // TTS may be unavailable (e.g. offline) — fall back to IDLE silently.
            if (this.state === STATES.SPEAKING) this.setState(STATES.IDLE);
        }
    }
    stopAudio() {
        if (this.currentAudioSource && this.isAudioPlaying) { try { this.currentAudioSource.stop(); } catch (e) {} this.isAudioPlaying = false; }
    }

    // ── State + halo ─────────────────────────────────────────
    setState(newState) {
        this.state = newState;
        this.statusLabel.textContent = newState;
        this.statePill.dataset.state = newState;
        this.statePillText.textContent = newState;
        this.sbState.textContent = 'state: ' + newState;
        const map = {
            IDLE: COLORS.rimuru, LISTENING: COLORS.halo, OBSERVING: COLORS.halo,
            THINKING: COLORS.divine, PLANNING: COLORS.divine, UNDERSTANDING: COLORS.divine,
            RETRIEVING_MEMORY: COLORS.divine, EXECUTING: COLORS.ok, VERIFYING: COLORS.ok,
            LEARNING: COLORS.ok, REFLECTING: COLORS.ok, SPEAKING: COLORS.halo,
            ERROR: COLORS.alert, OFFLINE: COLORS.muted, ASKING: COLORS.divine
        };
        this.statusLabel.style.color = map[newState] || COLORS.rimuru;
    }

    renderCanvas(forceStatic) {
        if (this.reducedMotion && !forceStatic) return;
        if (document.hidden && !forceStatic) { this.canvasRunning = false; return; }
        this.canvasRunning = true;
        this.time += 0.016;
        const ctx = this.ctx;
        const cx = this.centerX, cy = this.centerY;
        const radius = 100 * this.radiusScale;
        ctx.clearRect(0, 0, this.canvasWidth, this.canvasHeight);
        ctx.shadowBlur = 20; ctx.lineJoin = 'round'; ctx.lineCap = 'round';

        let mainColor, coreGlow, rotationSpeed;
        switch (this.state) {
            case STATES.IDLE: mainColor = COLORS.rimuru; coreGlow = `${COLORS.rimuru}40`; rotationSpeed = 0.5;
                this.drawHalo(cx, cy, radius, mainColor, this.time * rotationSpeed, 1); this.drawSigil(cx, cy, radius * 0.6, mainColor, -this.time * 0.3); break;
            case STATES.LISTENING: case STATES.OBSERVING: mainColor = COLORS.halo; coreGlow = `${COLORS.halo}80`;
                const amp = Math.sin(this.time * 5) * 0.5 + 0.5;
                ctx.strokeStyle = COLORS.halo; ctx.lineWidth = 2; ctx.shadowColor = COLORS.halo;
                for (let i = 0; i < 24; i++) {
                    const a = (i / 24) * Math.PI * 2 + this.time * 0.2;
                    const rAmp = radius + 20 + amp * 30 * Math.random();
                    ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * (radius + 5), cy + Math.sin(a) * (radius + 5));
                    ctx.lineTo(cx + Math.cos(a) * rAmp, cy + Math.sin(a) * rAmp); ctx.stroke();
                }
                this.drawHalo(cx, cy, radius, mainColor, this.time, 1.5 + amp * 0.5); this.drawSigil(cx, cy, radius * 0.6, mainColor, -this.time * 0.5); break;
            case STATES.THINKING: case STATES.PLANNING: case STATES.UNDERSTANDING: case STATES.RETRIEVING_MEMORY: case STATES.ASKING: mainColor = COLORS.divine; coreGlow = `${COLORS.divine}60`;
                ctx.strokeStyle = mainColor; ctx.shadowColor = mainColor; ctx.lineWidth = 4;
                for (let i = 0; i < 6; i++) {
                    const a = (i / 6) * Math.PI * 2 + this.time * 2;
                    ctx.beginPath(); ctx.arc(cx, cy, radius, a, a + Math.PI / 4); ctx.stroke();
                    const a2 = (i / 6) * Math.PI * 2 - this.time * 1.5;
                    ctx.beginPath(); ctx.arc(cx, cy, radius + 15, a2, a2 + Math.PI / 6); ctx.stroke();
                }
                this.drawSigil(cx, cy, radius * 0.6, mainColor, this.time); break;
            case STATES.EXECUTING: case STATES.VERIFYING: case STATES.LEARNING: case STATES.REFLECTING: mainColor = COLORS.ok; coreGlow = `${COLORS.ok}55`;
                ctx.strokeStyle = mainColor; ctx.shadowColor = mainColor; ctx.lineWidth = 3;
                for (let i = 0; i < 3; i++) { const rr = radius * (0.5 + i * 0.25); ctx.beginPath(); ctx.arc(cx, cy, rr, this.time * (1 + i), this.time * (1 + i) + Math.PI * 1.2); ctx.stroke(); }
                this.drawHalo(cx, cy, radius, mainColor, -this.time, 1.2); break;
            case STATES.SPEAKING: mainColor = COLORS.halo; coreGlow = `${COLORS.halo}80`;
                const sp = Math.sin(this.time * 8) * 0.5 + 0.5;
                ctx.strokeStyle = mainColor; ctx.shadowColor = mainColor;
                for (let i = 0; i < 3; i++) {
                    const rt = (this.time * 2 + i * 2) % 6;
                    if (rt < 3) { ctx.globalAlpha = 1 - (rt / 3); ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, radius + rt * 20, 0, Math.PI * 2); ctx.stroke(); }
                }
                ctx.globalAlpha = 1;
                this.drawHalo(cx, cy, radius, mainColor, this.time * 1.5, 2 + sp); this.drawSigil(cx, cy, radius * 0.6, mainColor, -this.time); break;
            case STATES.ERROR: mainColor = COLORS.alert; coreGlow = `${COLORS.alert}40`;
                this.drawHalo(cx, cy, radius, mainColor, this.time * 0.1, 1);
                ctx.font = `${24 * this.radiusScale}px JetBrains Mono`; ctx.fillStyle = mainColor; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('ERR', cx, cy); break;
            default: mainColor = COLORS.divine; coreGlow = `${COLORS.divine}40`;
                this.drawHalo(cx, cy, radius, mainColor, this.time * 3, 1.5); this.drawSigil(cx, cy, radius * 0.4, mainColor, -this.time * 2);
        }
        ctx.shadowBlur = 0;
        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        gradient.addColorStop(0, coreGlow); gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient; ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.fill();
        requestAnimationFrame(this.renderCanvas.bind(this));
    }

    drawHalo(cx, cy, radius, color, rotation, thicknessMulti) {
        const ctx = this.ctx;
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(rotation);
        ctx.strokeStyle = color; ctx.shadowColor = color; ctx.shadowBlur = 15;
        ctx.lineWidth = 2 * thicknessMulti; ctx.beginPath(); ctx.arc(0, 0, radius, 0, Math.PI * 2); ctx.stroke();
        ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(0, 0, radius + 8, 0, Math.PI * 2); ctx.stroke();
        ctx.lineWidth = 4 * thicknessMulti;
        for (let i = 0; i < 4; i++) { ctx.beginPath(); ctx.arc(0, 0, radius, i * Math.PI / 2, i * Math.PI / 2 + Math.PI / 4); ctx.stroke(); }
        ctx.restore();
    }

    drawSigil(cx, cy, radius, color, rotation) {
        const ctx = this.ctx;
        ctx.save(); ctx.translate(cx, cy); ctx.rotate(rotation);
        ctx.strokeStyle = color; ctx.shadowColor = color; ctx.shadowBlur = 10; ctx.lineWidth = 2;
        ctx.beginPath();
        for (let i = 0; i < 6; i++) { const a = (i / 6) * Math.PI * 2; if (i === 0) ctx.moveTo(Math.cos(a) * radius, Math.sin(a) * radius); else ctx.lineTo(Math.cos(a) * radius, Math.sin(a) * radius); }
        ctx.closePath(); ctx.stroke();
        ctx.beginPath();
        for (let i = 0; i < 3; i++) { const a = (i / 3) * Math.PI * 2 + Math.PI / 6; if (i === 0) ctx.moveTo(Math.cos(a) * radius * 0.7, Math.sin(a) * radius * 0.7); else ctx.lineTo(Math.cos(a) * radius * 0.7, Math.sin(a) * radius * 0.7); }
        ctx.closePath(); ctx.stroke();
        ctx.restore();
    }
}

document.addEventListener('DOMContentLoaded', () => { window.app = new RaphaelApp(); });
