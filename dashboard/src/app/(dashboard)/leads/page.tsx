"use client";

import { useState } from "react";
import { useAppContext } from "../../../lib/AppContext";
import { authenticatedFetch } from "../../../lib/api";
import { Lead } from "../../../lib/types";
import {
  UserCheck,
  Trash2,
  Eye,
  X,
  Mail,
  Phone,
  Calendar,
  Database,
  ExternalLink,
  Loader2,
  FolderOpen
} from "lucide-react";
import { useRouter } from "next/navigation";

export default function LeadsPage() {
  const router = useRouter();
  const {
    leads,
    isBackendOnline,
    loadBackendData
  } = useAppContext();

  // Search and Modal States
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);

  const handleDeleteLead = async (leadId: string) => {
    if (!confirm("¿Estás seguro de eliminar este prospecto permanentemente?")) return;
    
    setDeleteLoading(leadId);

    if (!isBackendOnline) {
      // Mock local deletion via simulated reload
      alert("Lead eliminado localmente (Mock Mode)");
      setDeleteLoading(null);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/leads/${leadId}`, {
        method: "DELETE"
      });

      if (res.ok) {
        await loadBackendData(); // Refrescar leads
        if (selectedLead?.id === leadId) {
          setSelectedLead(null);
        }
      } else {
        alert("Error al eliminar el prospecto.");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al intentar eliminar.");
    } finally {
      setDeleteLoading(null);
    }
  };

  const filteredLeads = leads.filter(lead => {
    const term = searchTerm.toLowerCase();
    return (
      lead.name.toLowerCase().includes(term) ||
      (lead.email && lead.email.toLowerCase().includes(term)) ||
      (lead.phone && lead.phone.toLowerCase().includes(term))
    );
  });

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12 animate-fadeIn text-xs">
      
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gray-900/10 border border-gray-850 p-6 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/15">
            <UserCheck className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Prospectos Capturados (Leads)</h3>
            <p className="text-[10px] text-gray-500">Contactos y campos calificados extraídos automáticamente por tus agentes de IA.</p>
          </div>
        </div>

        {/* Search Input */}
        <div className="w-full md:w-64">
          <input
            type="text"
            placeholder="Buscar por nombre, email..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-[#0c101c] border border-gray-850 focus:border-purple-500 rounded-xl px-4 py-2 text-white focus:outline-none"
          />
        </div>
      </div>

      {/* Leads Table Card */}
      <div className="glow-card rounded-2xl overflow-hidden border border-gray-850">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-gray-850 text-gray-400 font-semibold uppercase bg-gray-900/30">
                <th className="px-6 py-4">Nombre Completo</th>
                <th className="px-6 py-4">Email</th>
                <th className="px-6 py-4">Teléfono</th>
                <th className="px-6 py-4">Campos Calificados</th>
                <th className="px-6 py-4">Fecha Captura</th>
                <th className="px-6 py-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-850 text-[11px]">
              {filteredLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-850/20 transition-colors">
                  <td className="px-6 py-4 font-bold text-gray-250">
                    {lead.name}
                  </td>
                  <td className="px-6 py-4 text-gray-300">
                    {lead.email || (
                      <span className="text-gray-600 italic">No proporcionado</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-300">
                    {lead.phone || (
                      <span className="text-gray-600 italic">No proporcionado</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1.5 max-w-[280px]">
                      {lead.custom_data && Object.keys(lead.custom_data).length > 0 ? (
                        Object.entries(lead.custom_data).map(([key, val]) => (
                          <span 
                            key={key} 
                            className="px-2 py-0.5 bg-purple-950/45 border border-purple-500/15 text-purple-400 rounded-lg text-[9px] font-bold"
                          >
                            {key}: {String(val)}
                          </span>
                        ))
                      ) : (
                        <span className="text-gray-650 italic text-[10px]">Sin campos extra</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-500">
                    {new Date(lead.created_at).toLocaleDateString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setSelectedLead(lead)}
                        className="p-1.5 bg-blue-950/20 hover:bg-blue-900/30 text-blue-400 rounded-lg border border-blue-500/10 hover:border-blue-500/20 transition cursor-pointer"
                        title="Ver detalles"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        disabled={deleteLoading === lead.id}
                        onClick={() => handleDeleteLead(lead.id)}
                        className="p-1.5 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-lg border border-red-500/10 hover:border-red-500/20 transition disabled:opacity-40 cursor-pointer"
                        title="Eliminar lead"
                      >
                        {deleteLoading === lead.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredLeads.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-gray-500">
                    <FolderOpen className="w-8 h-8 mx-auto text-gray-650 mb-2" />
                    <p className="font-semibold text-xs">No se encontraron prospectos</p>
                    <p className="text-[10px] text-gray-550 mt-0.5">Los leads capturados por el Chat Sandbox o WhatsApp aparecerán aquí.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Modal */}
      {selectedLead && (
        <div className="fixed inset-0 bg-[#070b13]/85 backdrop-filter backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn text-xs">
          <div className="glow-card max-w-lg w-full rounded-2xl p-6 relative bg-[#0c101c]/95 border border-gray-800">
            {/* Close Button */}
            <button
              onClick={() => setSelectedLead(null)}
              className="absolute top-4 right-4 p-1.5 hover:bg-gray-800 rounded-xl transition text-gray-400 hover:text-white cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Modal Header */}
            <div className="flex items-center gap-3 border-b border-gray-850 pb-4 mb-4 pr-6">
              <div className="p-2.5 bg-purple-500/10 text-purple-400 rounded-xl border border-purple-500/15">
                <UserCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">{selectedLead.name}</h4>
                <p className="text-[9px] text-gray-500 font-semibold uppercase mt-0.5">Ficha del Lead</p>
              </div>
            </div>

            {/* Modal Body */}
            <div className="space-y-4">
              
              {/* Contact info grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="flex items-center gap-2 p-2.5 bg-[#070b13] border border-gray-850 rounded-xl">
                  <Mail className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="text-[9px] text-gray-500 block">Correo Electrónico</span>
                    <span className="text-gray-250 font-bold block truncate">{selectedLead.email || "No especificado"}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 p-2.5 bg-[#070b13] border border-gray-850 rounded-xl">
                  <Phone className="w-4 h-4 text-purple-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="text-[9px] text-gray-500 block">Teléfono / Celular</span>
                    <span className="text-gray-250 font-bold block truncate">{selectedLead.phone || "No especificado"}</span>
                  </div>
                </div>
              </div>

              {/* General dates / info */}
              <div className="flex justify-between items-center bg-gray-900/20 border border-gray-850/60 p-3 rounded-xl">
                <div className="flex items-center gap-1.5 text-gray-400">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Registrado el</span>
                </div>
                <span className="font-semibold text-gray-300">
                  {new Date(selectedLead.created_at).toLocaleString([], { dateStyle: 'long', timeStyle: 'short' })}
                </span>
              </div>

              {/* Custom data parser */}
              <div className="space-y-2">
                <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">Datos Calificados Extra</span>
                
                <div className="bg-[#070b13]/80 border border-gray-850 rounded-xl p-4 space-y-3">
                  {selectedLead.custom_data && Object.keys(selectedLead.custom_data).length > 0 ? (
                    Object.entries(selectedLead.custom_data).map(([key, val]) => (
                      <div key={key} className="flex justify-between items-center border-b border-gray-850/40 pb-2 last:border-b-0 last:pb-0">
                        <span className="font-bold text-purple-300">{key}</span>
                        <span className="font-semibold text-white bg-purple-950/20 border border-purple-900/10 px-2.5 py-0.5 rounded-lg">
                          {typeof val === "object" ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="flex flex-col items-center justify-center py-4 text-gray-500 italic">
                      <Database className="w-6 h-6 mb-1 text-gray-650" />
                      <span>No se extrajeron campos adicionales para este lead.</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Chat trace link */}
              {selectedLead.conversation_id && (
                <button
                  onClick={() => {
                    setSelectedLead(null);
                    router.push(`/conversations?id=${selectedLead.conversation_id}`);
                  }}
                  className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-gray-850 hover:bg-gray-800 text-gray-300 hover:text-white rounded-xl font-bold border border-gray-700 transition cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Ver Conversación de Origen
                </button>
              )}

            </div>

            {/* Footer Buttons */}
            <div className="flex gap-4 border-t border-gray-850 pt-4 mt-5">
              <button
                type="button"
                onClick={() => setSelectedLead(null)}
                className="flex-1 py-2 bg-gray-900 hover:bg-gray-850 text-gray-400 rounded-xl font-bold transition border border-gray-800 cursor-pointer"
              >
                Cerrar
              </button>
              <button
                type="button"
                onClick={() => handleDeleteLead(selectedLead.id)}
                className="py-2 px-4 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-xl font-bold border border-red-500/10 hover:border-red-500/20 transition cursor-pointer flex items-center justify-center gap-1.5"
              >
                <Trash2 className="w-4 h-4" />
                Eliminar Lead
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}
