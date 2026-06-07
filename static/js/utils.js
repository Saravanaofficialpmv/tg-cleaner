/**
 * Telegram Cleaner — Core utilities
 * Shared helpers used across all pages.
 */

/* ── Session ──────────────────────────────────────────────── */
const SESSION_KEY = 'tg_cleaner_session';

function getSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY)) || null;
  } catch { return null; }
}

function setSession(data) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(data));
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

function requireAuth(redirectTo = '/') {
  const session = getSession();
  if (!session || !session.session_id) {
    window.location.href = redirectTo;
    return null;
  }
  return session;
}

/* ── API helpers ──────────────────────────────────────────── */
const API_BASE = '/api';

async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
  };
  const config = { ...defaults, ...options };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  const res = await fetch(url, config);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

/* ── Toast notifications ──────────────────────────────────── */
let _toastContainer;

function getToastContainer() {
  if (!_toastContainer) {
    _toastContainer = document.createElement('div');
    _toastContainer.className = 'toast-container';
    document.body.appendChild(_toastContainer);
  }
  return _toastContainer;
}

function showToast(message, type = 'info', duration = 4000) {
  const icons = { success: '✓', error: '✕', info: 'ℹ', warn: '⚠' };
  const container = getToastContainer();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${escapeHtml(message)}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ── Formatting ───────────────────────────────────────────── */
function formatNumber(n) {
  if (n == null) return '—';
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
  return String(n);
}

function formatDate(isoString) {
  if (!isoString) return 'No activity';
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / 86_400_000);

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7)  return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}y ago`;
}

function isInactive(isoString, days = 30) {
  if (!isoString) return true;
  const d = new Date(isoString);
  return (new Date() - d) > days * 86_400_000;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ── Sidebar mobile toggle ────────────────────────────────── */
function initSidebar() {
  const toggle = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');

  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('visible');
  });

  overlay?.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
  });
}

/* ── Loading state helpers ────────────────────────────────── */
function setLoading(btn, loading, text = '') {
  if (!btn) return;
  if (loading) {
    btn.dataset.originalText = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span>${text ? ` ${text}` : ''}`;
    btn.disabled = true;
  } else {
    btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
    btn.disabled = false;
  }
}

/* ── Modal helpers ────────────────────────────────────────── */
function showModal(id) {
  document.getElementById(id)?.classList.add('visible');
}

function hideModal(id) {
  document.getElementById(id)?.classList.remove('visible');
}

/* ── Chat type label/badge ────────────────────────────────── */
function chatTypeBadge(type) {
  const map = {
    group:      '<span class="badge badge-group">Group</span>',
    channel:    '<span class="badge badge-channel">Channel</span>',
    supergroup: '<span class="badge badge-super">Supergroup</span>',
    megagroup:  '<span class="badge badge-super">Megagroup</span>',
    bot:        '<span class="badge badge-bot">Bot</span>',
    user:       '<span class="badge badge-user">Personal</span>',
  };
  return map[type] || `<span class="badge">${type}</span>`;
}

/* ── Avatar initials ──────────────────────────────────────── */
function getInitials(name = '') {
  return name.trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
}

function avatarColors(name = '') {
  const colors = [
    ['#ffcc4d','#d97706'], ['#1c1c1e','#2b2b2b'], ['#7a7a76','#a3a39e'],
    ['#ff9500','#ff5e00'], ['#e5e7eb','#9ca3af'], ['#10b981','#047857']
  ];
  let sum = 0;
  for (const ch of name) sum += ch.charCodeAt(0);
  const [c1, c2] = colors[sum % colors.length];
  return `linear-gradient(135deg, ${c1}, ${c2})`;
}

/* ── Init on load ─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initSidebar();

  // Highlight active nav link
  const path = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(el => {
    const href = el.getAttribute('href') || el.dataset.href;
    if (href && path.startsWith(href) && href !== '/') {
      el.classList.add('active');
    } else if (href === '/' && path === '/') {
      el.classList.add('active');
    }
  });

  // Create back to top button
  createBackToTopButton();
});

function createBackToTopButton() {
  const btn = document.createElement('button');
  btn.className = 'back-to-top';
  btn.innerHTML = '↑';
  btn.title = 'Back to top';
  btn.setAttribute('aria-label', 'Back to top');
  document.body.appendChild(btn);

  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      btn.classList.add('visible');
    } else {
      btn.classList.remove('visible');
    }
  });

  btn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}
