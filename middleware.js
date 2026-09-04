import { NextResponse } from 'next/server';

// Gate de acesso: exige cookie de sessão para ver o painel.
// A verificação forte da assinatura acontece nas rotas de API (runtime node).
// Aqui só checamos a presença/forma do cookie para redirecionar ao login.
const PUBLIC_PATHS = ['/login', '/api/login', '/api/logout', '/ole-bridge.js', '/favicon.ico', '/logo.png'];

export function middleware(req) {
  const { pathname } = req.nextUrl;

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/static') ||
    PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + '/'))
  ) {
    return NextResponse.next();
  }

  const cookie = req.cookies.get('ole_session');
  const looksValid = cookie && typeof cookie.value === 'string' && cookie.value.split('.').length === 2;

  if (!looksValid) {
    if (pathname.startsWith('/api/')) {
      return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
    }
    const url = req.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('next', pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
