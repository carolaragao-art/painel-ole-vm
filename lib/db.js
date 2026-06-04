// Conexão única (singleton) com o PostgreSQL e criação da tabela de estado.
const { Pool } = require('pg');

const connectionString =
  process.env.DATABASE_URL ||
  process.env.POSTGRES_URL ||
  process.env.POSTGRES_PRISMA_URL ||
  process.env.POSTGRES_URL_NON_POOLING;

let pool = global.__olePool;
if (!pool) {
  pool = new Pool({
    connectionString,
    ssl: connectionString && connectionString.includes('sslmode=disable')
      ? false
      : { rejectUnauthorized: false },
    max: 3,
  });
  global.__olePool = pool;
}

let ready = global.__oleReady;
async function ensureSchema() {
  if (ready) return ready;
  ready = pool.query(`
    CREATE TABLE IF NOT EXISTS kv_state (
      k          TEXT PRIMARY KEY,
      v          TEXT,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
  `);
  global.__oleReady = ready;
  return ready;
}

async function getAllState() {
  await ensureSchema();
  const { rows } = await pool.query('SELECT k, v FROM kv_state');
  const out = {};
  for (const r of rows) out[r.k] = r.v;
  return out;
}

// Retorna uma "versão" leve do estado (maior data de atualização + contagem).
// Usado pela sincronização automática: barato, não baixa todos os dados.
async function getStateVersion() {
  await ensureSchema();
  const { rows } = await pool.query(
    'SELECT COALESCE(MAX(updated_at)::text, \'\') AS max_ts, COUNT(*)::int AS n FROM kv_state'
  );
  const r = rows[0] || {};
  return { version: (r.max_ts || '') + '|' + (r.n || 0) };
}

async function setState(key, value) {
  await ensureSchema();
  if (value === null || value === undefined) {
    await pool.query('DELETE FROM kv_state WHERE k = $1', [key]);
    return;
  }
  await pool.query(
    `INSERT INTO kv_state (k, v, updated_at) VALUES ($1, $2, now())
     ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()`,
    [key, String(value)]
  );
}

async function importState(obj, force = false) {
  await ensureSchema();
  const keys = Object.keys(obj || {});
  let imported = 0;
  for (const k of keys) {
    const v = obj[k];
    if (v === null || v === undefined) continue;
    if (force) {
      await pool.query(
        `INSERT INTO kv_state (k, v, updated_at) VALUES ($1, $2, now())
         ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()`,
        [k, String(v)]
      );
      imported++;
    } else {
      const res = await pool.query(
        `INSERT INTO kv_state (k, v, updated_at) VALUES ($1, $2, now())
         ON CONFLICT (k) DO NOTHING`,
        [k, String(v)]
      );
      if (res.rowCount > 0) imported++;
    }
  }
  return imported;
}

module.exports = { pool, ensureSchema, getAllState, getStateVersion, setState, importState };
