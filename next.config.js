/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Garante que o painel.html seja incluído no bundle da função da rota "/"
  outputFileTracingIncludes: {
    '/': ['./public/painel.html'],
  },
};

module.exports = nextConfig;
