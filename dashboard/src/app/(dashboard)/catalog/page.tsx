"use client";

import { useState } from "react";
import {
  Package,
  Upload,
  Download,
  Plus,
  Search,
  Filter,
  Trash2,
  Edit2,
  CheckCircle2,
  XCircle,
  Sparkles,
  FileSpreadsheet,
  ExternalLink,
  DollarSign
} from "lucide-react";

interface CatalogItem {
  id: string;
  name: string;
  category: string;
  price: number;
  description: string;
  imageUrl?: string;
  isAvailable: boolean;
}

export default function CatalogPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Formulario nuevo item
  const [newItemName, setNewItemName] = useState("");
  const [newItemCategory, setNewItemCategory] = useState("Servicios");
  const [newItemPrice, setNewItemPrice] = useState("");
  const [newItemDesc, setNewItemDesc] = useState("");
  const [newItemImage, setNewItemImage] = useState("");

  const [items, setItems] = useState<CatalogItem[]>([
    {
      id: "cat-1",
      name: "Apartamento 402 — Laureles",
      category: "Inmuebles (Arriendo)",
      price: 2800000,
      description: "3 alcobas, 2 baños, parqueadero cubierto, estrato 5, cerca a parques.",
      imageUrl: "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=400",
      isAvailable: true
    },
    {
      id: "cat-2",
      name: "Limpieza Facial Profunda con Ozonoterapia",
      category: "Estética & Salud",
      price: 150000,
      description: "Exfoliación con punta de diamante, vapor de ozono y máscara descongestiva.",
      imageUrl: "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=400",
      isAvailable: true
    },
    {
      id: "cat-3",
      name: "Menú Degustación 5 Tiempos (2 Personas)",
      category: "Restaurantes",
      price: 220000,
      description: "Entrada gourmet, 2 fuertes de autor, postre de la casa y maridaje de vino.",
      imageUrl: "https://images.unsplash.com/photo-1544025162-d76694265947?w=400",
      isAvailable: true
    },
    {
      id: "cat-4",
      name: "Suite Loft Poblado — Vista Panorámica",
      category: "Rentas Cortas",
      price: 380000,
      description: "Hospedaje por noche para hasta 3 huéspedes, jacuzzi privado y Wi-Fi 300 Mbps.",
      imageUrl: "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=400",
      isAvailable: true
    },
    {
      id: "cat-5",
      name: "Mantenimiento Preventivo de Planta Eléctrica",
      category: "Operaciones & Soporte",
      price: 450000,
      description: "Revisión de filtros, aceite, calibración de panel y reporte técnico digital.",
      isAvailable: true
    }
  ]);

  const toggleAvailability = (id: string) => {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, isAvailable: !it.isAvailable } : it))
    );
  };

  const handleDeleteItem = (id: string) => {
    if (confirm("¿Estás seguro de eliminar este item del catálogo?")) {
      setItems((prev) => prev.filter((it) => it.id !== id));
    }
  };

  const handleCreateItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName || !newItemPrice) {
      alert("Por favor completa el nombre y el precio.");
      return;
    }

    const newItem: CatalogItem = {
      id: `cat-${Date.now()}`,
      name: newItemName,
      category: newItemCategory,
      price: Number(newItemPrice),
      description: newItemDesc,
      imageUrl: newItemImage || undefined,
      isAvailable: true
    };

    setItems([newItem, ...items]);
    setNewItemName("");
    setNewItemPrice("");
    setNewItemDesc("");
    setNewItemImage("");
    setShowCreateModal(false);
  };

  const downloadExcelTemplate = () => {
    const csvContent = "data:text/csv;charset=utf-8," + 
      "Nombre,Categoria,Precio_COP,Descripcion,Foto_URL,Disponible\n" +
      "Apartamento 301 Laureles,Inmuebles,2500000,3 alcobas 2 banos,https://ejemplo.com/foto.jpg,SI\n" +
      "Limpieza Facial,Estetica,120000,Duracion 60 minutos,https://ejemplo.com/facial.jpg,SI\n";
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "plantilla_catalogo_genia.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const categories = ["all", ...Array.from(new Set(items.map((i) => i.category)))];

  const filteredItems = items.filter((item) => {
    const matchesCategory = selectedCategory === "all" || item.category === selectedCategory;
    const matchesSearch =
      item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.description.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header con gradiente genia.com.co */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-indigo-500/10 border border-indigo-500/20 text-cyan-300 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-cyan-400" /> Inventario Inteligente
            </span>
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">
            Catálogo de <span className="bg-gradient-to-r from-[#4f46e5] via-[#6366f1] to-[#38bdf8] bg-clip-text text-transparent">Productos & Servicios</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Tu agente de IA consulta este catálogo en tiempo real para cotizar y enviar fotos a tus prospectos.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold border border-white/[0.08] transition cursor-pointer"
          >
            <Upload className="w-3.5 h-3.5 text-indigo-400" />
            <span>Cargar Excel / CSV</span>
          </button>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-gradient-to-r from-blue-600 via-indigo-600 to-indigo-700 hover:from-blue-500 hover:to-indigo-600 text-white rounded-xl text-xs font-bold border border-indigo-500/30 shadow-lg shadow-indigo-500/25 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Nuevo Item</span>
          </button>
        </div>
      </div>

      {/* Barra de Filtros */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-[#0b0f19] border border-white/[0.08] p-3 rounded-2xl">
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por nombre, servicio, propiedad o descripción..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#070a12] border border-white/[0.08] focus:border-indigo-500 rounded-xl pl-9 pr-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-[#070a12] text-slate-300 text-xs border border-white/[0.08] rounded-xl px-3 py-2 focus:outline-none cursor-pointer"
          >
            <option value="all">Todas las Categorías</option>
            {categories.filter((c) => c !== "all").map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabla de Productos / Servicios */}
      <div className="bg-[#0b0f19] border border-white/[0.08] rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-[#070a12]/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">Item / Producto</th>
                <th className="py-3.5 px-4">Categoría</th>
                <th className="py-3.5 px-4">Precio (COP)</th>
                <th className="py-3.5 px-4">Disponibilidad</th>
                <th className="py-3.5 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.06]">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      {item.imageUrl ? (
                        <img
                          src={item.imageUrl}
                          alt={item.name}
                          className="w-10 h-10 rounded-xl object-cover border border-white/[0.08]"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                          <Package className="w-5 h-5" />
                        </div>
                      )}
                      <div>
                        <p className="font-bold text-white text-xs">{item.name}</p>
                        <p className="text-[11px] text-slate-400 line-clamp-1 max-w-sm">{item.description}</p>
                      </div>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="px-2.5 py-1 rounded-md text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                      {item.category}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 font-mono font-bold text-white">
                    ${item.price.toLocaleString("es-CO")} COP
                  </td>

                  <td className="py-3.5 px-4">
                    <button
                      onClick={() => toggleAvailability(item.id)}
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-bold border transition cursor-pointer flex items-center gap-1.5 ${
                        item.isAvailable
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                      }`}
                    >
                      {item.isAvailable ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                      <span>{item.isAvailable ? "Disponible" : "Agotado"}</span>
                    </button>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => handleDeleteItem(item.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-400 transition cursor-pointer"
                      title="Eliminar item"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Carga Masiva Excel/CSV */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileSpreadsheet className="w-5 h-5 text-indigo-400" /> Cargar Catálogo (Excel / CSV)
              </h3>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-white p-1 text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs text-slate-300">
              <div className="border-2 border-dashed border-white/[0.15] hover:border-indigo-500/50 rounded-2xl p-8 text-center cursor-pointer transition">
                <Upload className="w-8 h-8 text-indigo-400 mx-auto mb-2" />
                <p className="font-semibold text-white">Arrastra tu archivo aquí o haz clic para seleccionar</p>
                <p className="text-slate-500 text-[11px] mt-1">Soporta formatos .xlsx, .xls y .csv</p>
              </div>

              <div className="flex items-center justify-between p-3 bg-[#070a12] border border-white/[0.08] rounded-xl">
                <span className="text-slate-400">¿No tienes el formato adecuado?</span>
                <button
                  onClick={downloadExcelTemplate}
                  className="text-cyan-300 hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" /> Descargar Plantilla Modelo
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-white/[0.08]">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 text-xs text-slate-400 hover:text-white cursor-pointer"
              >
                Cerrar
              </button>
              <button
                onClick={() => {
                  alert("Archivo procesado con éxito. 12 nuevos items agregados al catálogo.");
                  setShowUploadModal(false);
                }}
                className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white text-xs font-semibold rounded-xl cursor-pointer"
              >
                Subir y Procesar con IA
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Nuevo Item Individual */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
          <div className="bg-[#0b0f19] border border-white/[0.1] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <h3 className="text-base font-bold text-white">Agregar al Catálogo</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-sm cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateItem} className="space-y-3 text-xs">
              <div>
                <label className="block font-semibold text-slate-200 mb-1">Nombre</label>
                <input
                  type="text"
                  required
                  placeholder="Ej: Apto 301 / Consulta Médica / Plato Fuerte"
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block font-semibold text-slate-200 mb-1">Categoría</label>
                  <input
                    type="text"
                    required
                    placeholder="Ej: Inmuebles / Tratamientos"
                    value={newItemCategory}
                    onChange={(e) => setNewItemCategory(e.target.value)}
                    className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-200 mb-1">Precio COP</label>
                  <input
                    type="number"
                    required
                    placeholder="Ej: 350000"
                    value={newItemPrice}
                    onChange={(e) => setNewItemPrice(e.target.value)}
                    className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-200 mb-1">Descripción</label>
                <textarea
                  rows={3}
                  placeholder="Detalles clave que el agente explicará al cliente..."
                  value={newItemDesc}
                  onChange={(e) => setNewItemDesc(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 resize-none"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-200 mb-1">URL de Foto (Opcional)</label>
                <input
                  type="url"
                  placeholder="https://images.unsplash.com/..."
                  value={newItemImage}
                  onChange={(e) => setNewItemImage(e.target.value)}
                  className="w-full bg-[#070a12] border border-white/[0.1] rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-white/[0.08]">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-1.5 text-slate-400 hover:text-white cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold rounded-xl cursor-pointer"
                >
                  Guardar Item
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
