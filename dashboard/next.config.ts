import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      {
        source: "/",
        destination: "/index.html",
      },
      {
        source: "/planes",
        destination: "/planes.html",
      },
      {
        source: "/cotizador",
        destination: "/cotizador.html",
      },
      {
        source: "/privacidad",
        destination: "/privacidad.html",
      },
      {
        source: "/terminos",
        destination: "/terminos.html",
      },
      {
        source: "/preonboarding",
        destination: "/infopreonboarding.html",
      },
    ];
  },
};

export default nextConfig;
