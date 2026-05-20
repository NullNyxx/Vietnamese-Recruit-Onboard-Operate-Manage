/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const apiUrl = process.env.INTERNAL_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/gmail/:path*",
        destination: `${apiUrl}/api/gmail/:path*`,
      },
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
