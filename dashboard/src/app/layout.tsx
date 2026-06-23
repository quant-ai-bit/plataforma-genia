import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "../lib/AppContext";

export const metadata: Metadata = {
  title: "GENIA — IA Automation Platform",
  description: "Plataforma de automatización de agentes de IA y captura de leads",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="antialiased bg-[#0b0f19] text-gray-100 min-h-screen">
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}

