import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "../lib/AppContext";

export const metadata: Metadata = {
  title: "GENIA — Plataforma de Agentes de IA & CRM Autónomo",
  description: "Ecosistema integral de agentes autónomos de Inteligencia Artificial, CRM y automatizaciones.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased bg-[#070a12] text-slate-100 min-h-screen selection:bg-indigo-500/30 selection:text-indigo-200">
        <AppProvider>
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
