// Autenticação simples por cookie assinado (HMAC-SHA256). Sem dependências externas.
const crypto = require('crypto');

const COOKIE_NAME = 'ole_session';
const MAX_AGE = 60 * 60 * 24 * 30; // 30 dias

function secret() {
  return process.env.AUTH_SECRET || 'dev-secret-trocar-em-producao';
}

function getUsers() {
  const raw = process.env.AUTH_USERS || 'admin:admin';
  const map = {};
  raw.split(',').forEach((pair) => {
    const idx = pair.indexOf(':');
    if (idx === -1) return;
    const u = pair.slice(0, idx).trim().toLowerCase();
    const p = pair.slice(idx + 1).trim();
    if (u) map[u] = p;
  });
  return map;
}

function checkCredentials(user, pass) {
  const users = getUsers();
  const u = String(user || '').trim().toLowerCase();
  return users[u] !== undefined && users[u] === String(pass || '');
}

function sign(value) {
  return crypto.createHmac('sha256', secret()).update(value).digest('base64url');
}

function makeToken(user) {
  const payload = `${user}.${Date.now()}`;
  const b64 = Buffer.from(payload).toString('base64url');
  return `${b64}.${sign(b64)}`;
}

function verifyToken(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [b64, sig] = parts;
  const expected = sign(b64);
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try {
    const payload = Buffer.from(b64, 'base64url').toString('utf8');
    const [user] = payload.split('.');
    return { user };
  } catch (e) {
    return null;
  }
}

function buildCookie(token) {
  return `${COOKIE_NAME}=${token}; Path=/; HttpOnly; SameSite=Lax; Secure; Max-Age=${MAX_AGE}`;
}
function clearCookie() {
  return `${COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Secure; Max-Age=0`;
}
function readCookie(req) {
  const header = req.headers.cookie || '';
  const found = header.split(';').map((c) => c.trim()).find((c) => c.startsWith(`${COOKIE_NAME}=`));
  if (!found) return null;
  return found.slice(COOKIE_NAME.length + 1);
}
function getSession(req) {
  return verifyToken(readCookie(req));
}

module.exports = {
  COOKIE_NAME, checkCredentials, makeToken, verifyToken,
  buildCookie, clearCookie, readCookie, getSession,
};
