import { useState } from 'react';
import { useRouter } from 'next/router';

export default function Login() {
  const router = useRouter();
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setErr('');
    setLoading(true);
    try {
      const r = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user, pass }),
      });
      if (r.ok) {
        const next = router.query.next && String(router.query.next).startsWith('/') ? String(router.query.next) : '/';
        window.location.href = next;
      } else {
        const d = await r.json().catch(() => ({}));
        setErr(d.error || 'Falha no login');
      }
    } catch (e) {
      setErr('Erro de conexão');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.wrap}>
      <form onSubmit={submit} style={styles.card}>
        <img src="/logo.png" alt="Olé Casas · Viana e Moura Construções" style={styles.logoMark} />
        <h1 style={styles.title}>Painel Executivo</h1>
        <p style={styles.sub}>Olé Casas × Viana e Moura</p>

        <label style={styles.label}>Usuário</label>
        <input
          autoFocus
          value={user}
          onChange={(e) => setUser(e.target.value)}
          style={styles.input}
          placeholder="seu usuário"
        />

        <label style={styles.label}>Senha</label>
        <input
          type="password"
          value={pass}
          onChange={(e) => setPass(e.target.value)}
          style={styles.input}
          placeholder="sua senha"
        />

        {err ? <div style={styles.err}>{err}</div> : null}

        <button type="submit" disabled={loading} style={styles.btn}>
          {loading ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}

const styles = {
  wrap: {
    minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: 'linear-gradient(135deg,#1D3461,#2a4a8a)', fontFamily: 'Poppins, system-ui, sans-serif', padding: 20,
  },
  card: {
    background: '#fff', borderRadius: 16, padding: '36px 32px', width: '100%', maxWidth: 360,
    boxShadow: '0 20px 60px rgba(0,0,0,.3)', display: 'flex', flexDirection: 'column',
  },
  logoMark: { height: 44, width: 'auto', maxWidth: '100%', display: 'block', marginBottom: 18 },
  title: { fontSize: 22, color: '#1D3461', margin: 0, fontWeight: 700 },
  sub: { fontSize: 13, color: '#64748b', marginTop: 4, marginBottom: 24 },
  label: { fontSize: 12, fontWeight: 600, color: '#64748b', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '.5px' },
  input: {
    border: '1.5px solid #e2e8f0', borderRadius: 8, padding: '11px 12px', fontSize: 14,
    marginBottom: 16, outline: 'none', fontFamily: 'inherit',
  },
  err: { background: '#fef2f2', color: '#dc2626', borderRadius: 8, padding: '9px 12px', fontSize: 13, marginBottom: 14 },
  btn: {
    background: '#E8622A', color: '#fff', border: 'none', borderRadius: 8, padding: '12px',
    fontSize: 15, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
  },
};
