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
async function ensureToken() {
    const cached = localStorage.getItem('raphael_token');
    if (cached) return cached;
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
    }
    return '';
}

window.RaphaelApi = {
    /** Local /ws URL with the bootstrap token appended. */
    defaultWsUrl() {
        const token = localStorage.getItem('raphael_token') || '';
        const base = BACKEND_ORIGIN.replace(/^http/, 'ws') + '/ws';
        return token ? `${base}?token=${encodeURIComponent(token)}` : base;
    },

    /** GET /health on the backend. */
    health() {
        return fetch(`${BACKEND_ORIGIN}/health`);
    },

    /**
     * Connect to the /ws WebSocket endpoint.
     * handlers: { onopen, onmessage, onclose, onerror }.
     * Ensures a token is present (bootstrap) before opening, and appends it
     * to the handshake URL. Returns the WebSocket, or null if construction threw.
     */
    async connect(serverUrl, handlers) {
        await ensureToken();
        let wsUrl = normalizeWsUrl(serverUrl) || RaphaelApi.defaultWsUrl();
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
        const token = localStorage.getItem('raphael_token') || '';
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        const response = await fetch(`${BACKEND_ORIGIN}/api/tts`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ text: text })
        });
        if (!response.ok) throw new Error('TTS request failed');
        return await response.arrayBuffer();
    }
};
