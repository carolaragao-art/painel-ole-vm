/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Garante que o painel.html seja incluído no bundle da função da rota "/"
  outputFileTracingIncludes: {
    '/': ['./public/painel.html'],
    '/api/pagina': ['./public/marcos.html', './public/projetos.html'],
  },
  // marcos.html e projetos.html passam a vir do banco (gravados por /api/importar).
  // "beforeFiles" faz a versão dinâmica ganhar do arquivo estático de public/,
  // que fica como reserva caso o banco esteja vazio.
  async rewrites() {
    return {
      beforeFiles: [
        { source: '/marcos.html', destination: '/api/pagina?nome=marcos' },
        { source: '/projetos.html', destination: '/api/pagina?nome=projetos' },
      ],
    };
  },
  // /painel.html é o arquivo cru em public/: abre sem o estado do banco e mostra
  // o que estiver no localStorage daquele navegador — dado velho, sem aviso.
  // O painel de verdade é a raiz, que injeta o estado e a ponte com o Postgres.
  async redirects() {
    return [{ source: '/painel.html', destination: '/', permanent: false }];
  },
};

module.exports = nextConfig;
