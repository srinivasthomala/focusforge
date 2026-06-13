/** @type {import('next').NextConfig} */
// The browser calls /api/* on the web origin; Next proxies it to the FastAPI
// backend server-side. API_URL is a server-only env var (no NEXT_PUBLIC_ needed
// — the API origin is never exposed to the client). Defaults to local dev.
const API_URL = process.env.API_URL || 'http://localhost:8000';

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_URL}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;


