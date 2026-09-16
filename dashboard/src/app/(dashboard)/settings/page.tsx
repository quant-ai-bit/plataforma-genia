"use client";

import { useState } from "react";
import {
  Building2,
  Clock,
  Phone,
  Mail,
  Save,
  CheckCircle2,
  Sparkles,
  ShieldAlert,
  Users
} from "lucide-react";

export default function SettingsPage() {
  const [businessName, setBusinessName] = useState("GENIA Cliente");
  const [industry, setIndustry] = useState("bienes_raices");
  const [advisorPhone, setAdvisorPhone] = useState("573105551234");
  const [advisorEmail, setAdvisorEmail] = useState("contacto@empresa.com");
  const [hours, setHours] = useState("Lunes a Viernes: 8:00 AM - 6:00 PM | Sábados: 9:00 AM - 1:00 PM");
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="max-w-4xl space-y-8 animate-fadeIn">
      {/* Header con gradiente genia.com.co */}
      <div className="border-b border-white/[0.08] pb-6">
        <div className="flex items-center gap-2 mb-1">
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/20 text-cyan-300 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-cyan-400" /> Perfil Operativo
          </span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">
          Mi <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Negocio</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          Configura la identidad de tu empresa, horarios de atención y canales de notificación.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <div className="bg-[#0b0f19] border border-white/[0.08] p-6 rounded-2xl space-y-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Building2 className="w-5 h-5 text-indigo-400" /> Datos de la Empresa
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-200 mb-1.5">Nombre Comercial</label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-200 mb-1.5">Sector o Industria</label>
              <select
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-indigo-500 cursor-pointer"
              >
                <option value="bienes_raices">🏠 Bienes Raíces & Inmobiliaria</option>
                <option value="restaurantes">🍽️ Restaurante & Gastronomía</option>
                <option value="clinicas">💉 Clínica Estética & Salud</option>
                <option value="rentas_cortas">🏖️ Rentas Cortas & Hospedaje</option>
                <option value="operaciones">⚙️ Servicios & Operaciones</option>
                <option value="comercio">🛍️ Comercio & Retail</option>
              </select>
            </div>
          </div>
        </div>

        <div className="bg-[#0b0f19] border border-white/[0.08] p-6 rounded-2xl space-y-5">
          <h3 className="text-base font-bold text-white flex items-center gap-2 border-b border-white/[0.06] pb-3">
            <Phone className="w-5 h-5 text-emerald-400" /> Canales de Notificación de Leads
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-200 mb-1.5">
                WhatsApp del Asesor (para avisos inmediatos)
              </label>
              <input
                type="text"
                value={advisorPhone}
                onChange={(e) => setAdvisorPhone(e.target.value)}
                className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-emerald-500"
              />
              <span className="text-[10px] text-slate-500 mt-1 block">Incluye código de país (ej: 57310...)</span>
            </div>

            <div>
              <label className="block font-semibold text-slate-200 mb-1.5">
                Correo Electrónico para Resumen Diario
              </label>
              <input
                type="email"
                value={advisorEmail}
                onChange={(e) => setAdvisorEmail(e.target.value)}
                className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="text-xs pt-2">
            <label className="block font-semibold text-slate-200 mb-1.5">
              Horario Habitual de Atención Humana
            </label>
            <input
              type="text"
              value={hours}
              onChange={(e) => setHours(e.target.value)}
              className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3.5 py-2.5 text-white focus:outline-none focus:border-indigo-500"
            />
            <span className="text-[10px] text-slate-500 mt-1 block">
              El agente de IA atiende 24/7, pero informará este horario cuando un cliente solicite llamada de un asesor.
            </span>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          {saved && (
            <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4" /> Cambios guardados con éxito
            </span>
          )}

          <button
            type="submit"
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white text-xs font-bold rounded-xl border border-indigo-500/30 shadow-lg shadow-indigo-500/25 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>Guardar Configuración</span>
          </button>
        </div>
      </form>
    </div>
  );
}
