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
};

module.exports = nextConfig;
