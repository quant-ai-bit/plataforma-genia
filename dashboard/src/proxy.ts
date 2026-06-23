import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function proxy(request: NextRequest) {
  // Dado que el cliente de Supabase estándar almacena la sesión en localStorage (del navegador),
  // la protección y redirección se maneja principalmente en el lado del cliente (AuthGuard en layouts)
  // para evitar falsos negativos en el servidor.
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Coincidir con todas las rutas excepto:
     * - api (rutas de backend expuestas en Vercel)
     * - _next/static (archivos estáticos de Next.js)
     * - _next/image (optimización de imágenes)
     * - favicon.ico (icono de la pestaña)
     */
    "/((?!api|_next/static|_next/image|favicon.ico).*)",
  ],
};
