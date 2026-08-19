// ── Raphael frontend API service layer ────────────────────────────────────────
// All backend communication (REST + WebSocket) flows through window.RaphaelApi.
// Loaded before app.js via <script> in index.html.
//
// Target backend: the local Raphael Always-Alive gateway on localhost:8765
// (see raphael/network/api.py). Every REST route and the WS handshake require
// the api_token. The token is obtained once from the loopback-only
// /api/bootstrap endpoint and cached in localStorage (see ensureToken()).

const BACKEND_ORIGIN = 'http://localhost:8765';

// ── Shared WebSocket URL normalizer ─────────────────────────────────────────
function normalizeWsUrl(raw) {
    if (typeof raw !== 'string') return null;
    let url = raw.trim();
    if (!url) return null;
    if (url.startsWith('https://')) {
        url = 'wss://' + url.slice('https://'.length);
    } else if (url.startsWith('http://')) {
        url = 'ws://' + url.slice('http://'.length);
    }
    if (!url.startsWith('ws://') && !url.startsWith('wss://')) {
        const host = (typeof window !== 'undefined' && window.location && window.location.host) || '';
        if (host && url.includes(host)) return null;
        const proto = (typeof window !== 'undefined' && window.location && window.location.protocol === 'https:') ? 'wss:' : 'ws:';
        url = `${proto}//${host}${url.startsWith('/') ? '' : '/'}${url}`;
    }
    if (!url.includes('/ws')) {
        url = url.replace(/\/$/, '') + '/ws';
    }
    if (!url.startsWith('ws://') && !url.startsWith('wss://')) return null;
    return url;
}

// ── Token bootstrap (loopback only) ────────────────────────────────────────
// Mirrors the React client: fetch the token from /api/bootstrap, cache it.
let tokenRequest = null;

async function ensureToken() {
    const cached = localStorage.getItem('raphael_token');
    if (cached) return cached;

    // Startup opens a socket and several REST panels at once. Share one
    // bootstrap request so none of those callers proceeds with an empty token.
    if (!tokenRequest) {
        tokenRequest = (async () => {
            try {
                const res = await fetch(`${BACKEND_ORIGIN}/api/bootstrap`);
                if (res.ok) {
                    const data = await res.json();
                    if (data && data.token) {
                        localStorage.setItem('raphael_token', data.token);
                        return data.token;
                    }
                }
            } catch (e) {
                console.warn('[auth] bootstrap failed (server down?):', e);
            } finally {
                tokenRequest = null;
            }
            return '';
        })();
    }
    return tokenRequest;
}

async function authHeaders(contentType = false) {
    const token = await ensureToken();
    const headers = contentType ? { 'Content-Type': 'application/json' } : {};
    if (token) headers.Authorization = `Bearer ${token}`;
    return headers;
}

function withLocalToken(wsUrl, token) {
    if (!token) return wsUrl;
    try {
        const url = new URL(wsUrl);
        // Never leak the local assistant token to a user-configured remote WS.
        if (!['localhost', '127.0.0.1', '::1'].includes(url.hostname) || url.searchParams.has('token')) {
            return wsUrl;
        }
        url.searchParams.set('token', token);
        return url.toString();
    } catch (_) {
        return wsUrl;
    }
}

window.RaphaelApi = {
    /** Local /ws URL with the bootstrap token appended. */
    defaultWsUrl() {
        const token = localStorage.getItem('raphael_token') || '';
        const base = BACKEND_ORIGIN.replace(/^http/, 'ws') + '/ws';
        return token ? `${base}?token=${encodeURIComponent(token)}` : base;
    },

    /** GET /status — public state + system metrics. */
    async status() {
        const res = await fetch(`${BACKEND_ORIGIN}/status`);
        if (!res.ok) throw new Error('status failed');
        return await res.json();
    },

    /** GET /api/tasks (auth-gated) — list background tasks. */
    async listTasks() {
        const headers = await authHeaders();
        const res = await fetch(`${BACKEND_ORIGIN}/api/tasks`, { headers });
        if (!res.ok) throw new Error('listTasks failed');
        return await res.json();
    },

    /** POST /api/tasks/{id}/{act} where act ∈ pause|resume|cancel|retry. */
    async taskAction(act, id) {
        const headers = await authHeaders(true);
        const res = await fetch(`${BACKEND_ORIGIN}/api/tasks/${encodeURIComponent(id)}/${act}`, { method: 'POST', headers });
        if (!res.ok) throw new Error('taskAction failed');
        return await res.json();
    },

    /** GET /api/memories (auth-gated) — list long-term memories. */
    async listMemories() {
        const headers = await authHeaders();
        const res = await fetch(`${BACKEND_ORIGIN}/api/memories`, { headers });
        if (!res.ok) throw new Error('listMemories failed');
        return await res.json();
    },

    /** POST /api/runtime/mode — set the always-alive runtime mode. */
    async setMode(mode) {
        const headers = await authHeaders(true);
        const res = await fetch(`${BACKEND_ORIGIN}/api/runtime/mode`, { method: 'POST', headers, body: JSON.stringify({ mode }) });
        if (!res.ok) throw new Error('setMode failed');
        return await res.json();
    },

    /** POST /api/runtime/interrupt — interrupt the runtime. */
    async interrupt() {
        const headers = await authHeaders(true);
        const res = await fetch(`${BACKEND_ORIGIN}/api/runtime/interrupt`, { method: 'POST', headers });
        if (!res.ok) throw new Error('interrupt failed');
        return await res.json();
    },

    /**
     * Connect to the /ws WebSocket endpoint.
     * handlers: { onopen, onmessage, onclose, onerror }.
     * Ensures a token is present (bootstrap) before opening, and appends it
     * to the handshake URL. Returns the WebSocket, or null if construction threw.
     */
    async connect(serverUrl, handlers) {
        const token = await ensureToken();
        let wsUrl = normalizeWsUrl(serverUrl) || RaphaelApi.defaultWsUrl();
        wsUrl = withLocalToken(wsUrl, token);
        try {
            const ws = new WebSocket(wsUrl);
            if (handlers.onopen) ws.onopen = handlers.onopen;
            if (handlers.onmessage) ws.onmessage = handlers.onmessage;
            if (handlers.onclose) ws.onclose = handlers.onclose;
            if (handlers.onerror) ws.onerror = handlers.onerror;
            return ws;
        } catch (e) {
            console.error('WebSocket connection failed:', e);
            return null;
        }
    },

    /** Serialize and send a chat payload over an open WebSocket. */
    send(ws, payload) {
        ws.send(JSON.stringify(payload));
    },

    /** POST /tts — returns the decoded audio ArrayBuffer (throws on non-OK). */
    async tts(text) {
        const headers = await authHeaders(true);
        const response = await fetch(`${BACKEND_ORIGIN}/api/tts`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) throw new Error('TTS request failed');
        return await response.arrayBuffer();
    }
};
