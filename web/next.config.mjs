/** @type {import('next').NextConfig} */
const nextConfig = {
  // better-sqlite3 is a native module; keep it external on the server.
  serverExternalPackages: ["better-sqlite3"],
};

export default nextConfig;
