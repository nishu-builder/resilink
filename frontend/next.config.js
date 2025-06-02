/* eslint-disable @typescript-eslint/no-var-requires */
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    appDir: true,
  },
  images: {
    unoptimized: true,
  },
};

module.exports = nextConfig; 