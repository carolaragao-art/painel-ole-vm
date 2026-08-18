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

// ── Usuários no banco (tabela auth_users) ─────────────────────
// Permite administrar logins pelo próprio painel, sem redeploy.
// Na primeira utilização, importa automaticamente os usuários da
// env var AUTH_USERS (com hash). Se o banco falhar, o login cai
// no modo antigo (env) para ninguém ficar trancado do lado de fora.
function hashSenha(user, pass) {
  return crypto.createHmac('sha256', secret()).update(`${String(user).trim().toLowerCase()}:${String(pass)}`).digest('base64url');
}

let authUsersReady = global.__oleAuthUsersReady;
async function ensureAuthUsers() {
  const { pool } = require('./db');
  if (authUsersReady) return authUsersReady;
  authUsersReady = pool.query(`
    CREATE TABLE IF NOT EXISTS auth_users (
      usuario    TEXT PRIMARY KEY,
      hash       TEXT NOT NULL,
      criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
  global.__oleAuthUsersReady = authUsersReady;
  return authUsersReady;
}

async function seedFromEnvIfEmpty() {
  const { pool } = require('./db');
  const { rows } = await pool.query('SELECT COUNT(*)::int AS n FROM auth_users');
  if (rows[0].n > 0) return;
  const users = getUsers();
  for (const u of Object.keys(users)) {
    await pool.query(
      'INSERT INTO auth_users (usuario, hash) VALUES ($1, $2) ON CONFLICT (usuario) DO NOTHING',
      [u, hashSenha(u, users[u])]
    );
  }
}

async function checkCredentialsAsync(user, pass) {
  const u = String(user || '').trim().toLowerCase();
  if (!u) return false;
  try {
    const { pool } = require('./db');
    await ensureAuthUsers();
    await seedFromEnvIfEmpty();
    const { rows } = await pool.query('SELECT hash FROM auth_users WHERE usuario = $1', [u]);
    if (!rows.length) return false;
    const esperado = Buffer.from(rows[0].hash);
    const recebido = Buffer.from(hashSenha(u, pass));
    return esperado.length === recebido.length && crypto.timingSafeEqual(esperado, recebido);
  } catch (e) {
    console.error('auth_users indisponivel, usando env:', e.message);
    return checkCredentials(user, pass);
  }
}

module.exports = {
  COOKIE_NAME, checkCredentials, checkCredentialsAsync, makeToken, verifyToken,
  buildCookie, clearCookie, readCookie, getSession,
  hashSenha, ensureAuthUsers, seedFromEnvIfEmpty,
};
