/** @type {import('next').NextConfig} */
const API_PORT = process.env.API_PORT || 8000;

const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `http://127.0.0.1:${API_PORT}/api/:path*`
      }
    ]
  }
};

export default nextConfig;
