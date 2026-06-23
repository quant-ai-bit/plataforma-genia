"use client";

import React, { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../../lib/AppContext";
import { authenticatedFetch } from "../../../../lib/api";
import { Agent, KbImage } from "../../../../lib/types";
import {
  ArrowLeft,
  Bot,
  Globe,
  Phone,
  MessageSquare,
  Send,
  Calendar,
  Database,
  Shield,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronRight,
  Plus,
  Edit,
  Trash2,
  X,
  CheckCircle,
  Loader2,
  FolderOpen,
  Upload
} from "lucide-react";

export default function AgentConfigPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  
  const {
    agents,
    isBackendOnline,
    availableModels,
    loadBackendData
  } = useAppContext();

  // Agent State
  const [agent, setAgent] = useState<Agent | null>(null);
  const [saveLoading, setSaveLoading] = useState<boolean>(false);

  // Form State
  const [form, setForm] = useState({
    name: "",
    description: "",
    system_prompt: "",
    provider: "groq",
    model: "llama-3.3-70b-versatile",
    temperature: 0.7,
    max_tokens: 1024,
    custom_fields: [] as any[],
    channels: [] as string[],
    notification_phone: ""
  });

  // Collapsible Sections
  const [expandedSections, setExpandedSections] = useState({
    general: true,
    llm: true,
    prompt: true,
    fields: true,
    channels: true,
    advanced: false,
    visual: true
  });

  // Custom Fields Editing State
  const [newField, setNewField] = useState({
    key: "",
    label: "",
    type: "string",
    required: false,
    description: ""
  });
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null);

  // Visual Training State
  const [kbImages, setKbImages] = useState<KbImage[]>([]);
  const [kbImagesLoading, setKbImagesLoading] = useState<boolean>(false);
  const [uploadImageFile, setUploadImageFile] = useState<File | null>(null);
  const [detectedProduct, setDetectedProduct] = useState<string>("");
  const [imagePrice, setImagePrice] = useState<string>("");
  const [imageDescription, setImageDescription] = useState<string>("");
  const [imageKeywords, setImageKeywords] = useState<string>("");
  const [suggestedRule, setSuggestedRule] = useState<string>("");
  const [addToPrompt, setAddToPrompt] = useState<boolean>(true);
  const [uploadImageStep, setUploadImageStep] = useState<"select" | "analyzing" | "confirm" | "success">("select");
  const [isUploadingImage, setIsUploadingImage] = useState<boolean>(false);
  const [detectedImageId, setDetectedImageId] = useState<string | null>(null);
  const [detectedImageUrl, setDetectedImageUrl] = useState<string>("");

  useEffect(() => {
    const foundAgent = agents.find(a => a.id === id);
    if (foundAgent) {
      setAgent(foundAgent);
      setForm({
        name: foundAgent.name,
        description: foundAgent.description || "",
        system_prompt: foundAgent.system_prompt,
        provider: foundAgent.provider,
        model: foundAgent.model,
        temperature: foundAgent.temperature,
        max_tokens: foundAgent.max_tokens,
        custom_fields: foundAgent.custom_fields || [],
        channels: foundAgent.channels || ["web"],
        notification_phone: foundAgent.notification_phone || ""
      });
    }
  }, [id, agents]);

  useEffect(() => {
    if (id) {
      loadKbImages();
    }
  }, [id, isBackendOnline]);

  const loadKbImages = async () => {
    setKbImagesLoading(true);
    if (!isBackendOnline) {
      // Mock images
      setKbImages([
        { id: "img-1", agent_id: id, filename: "oficina_reunion.jpg", description: "Sala de reuniones moderna con proyector", url: "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=600&q=80", uploaded_at: new Date().toISOString() },
        { id: "img-2", agent_id: id, filename: "sala_juntas.jpg", description: "Sala de juntas premium con capacidad de 10 personas", url: "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=600&q=80", uploaded_at: new Date().toISOString() }
      ]);
      setKbImagesLoading(false);
      return;
    }
    try {
      const res = await authenticatedFetch(`/api/agents/${id}/images`);
      if (res.ok) {
        const data = await res.json();
        setKbImages(data);
      }
    } catch (err) {
      console.error("Error al cargar imágenes visuales:", err);
    } finally {
      setKbImagesLoading(false);
    }
  };

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleProviderChange = (provider: string) => {
    let defaultModel = "llama-3.3-70b-versatile";
    if (provider === "gemini") {
      defaultModel = "gemini-2.5-flash";
    } else if (provider === "openrouter") {
      defaultModel = "deepseek/deepseek-chat";
    }
    setForm(prev => ({ ...prev, provider, model: defaultModel }));
  };

  // Custom Fields Functions
  const addCustomField = () => {
    if (!newField.key.trim() || !newField.label.trim()) return;

    if (editingFieldIndex !== null) {
      setForm(prev => {
        const updated = [...prev.custom_fields];
        updated[editingFieldIndex] = { ...newField };
        return { ...prev, custom_fields: updated };
      });
      setEditingFieldIndex(null);
    } else {
      setForm(prev => ({
        ...prev,
        custom_fields: [...prev.custom_fields, { ...newField }]
      }));
    }
    setNewField({ key: "", label: "", type: "string", required: false, description: "" });
  };

  const removeCustomField = (index: number) => {
    setForm(prev => ({
      ...prev,
      custom_fields: prev.custom_fields.filter((_, idx) => idx !== index)
    }));
    if (editingFieldIndex === index) {
      setEditingFieldIndex(null);
      setNewField({ key: "", label: "", type: "string", required: false, description: "" });
    } else if (editingFieldIndex !== null && editingFieldIndex > index) {
      setEditingFieldIndex(editingFieldIndex - 1);
    }
  };

  const startEditCustomField = (index: number) => {
    const f = form.custom_fields[index];
    if (!f) return;
    setNewField({
      key: f.key,
      label: f.label,
      type: f.type || "string",
      required: !!f.required,
      description: f.description || ""
    });
    setEditingFieldIndex(index);
  };

  const cancelEditCustomField = () => {
    setEditingFieldIndex(null);
    setNewField({ key: "", label: "", type: "string", required: false, description: "" });
  };

  // Visual Training Actions
  const handleUploadAndGenerateTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadImageFile || !id || !detectedProduct || !imageDescription || !imagePrice) return;
    
    setUploadImageStep("analyzing");
    setIsUploadingImage(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setDetectedImageId(`img-${Date.now()}`);
        setDetectedImageUrl("https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=600&q=80");
        setSuggestedRule(`Si el usuario pregunta por ${detectedProduct}, describe el producto y muestra la foto usando: ![${detectedProduct}](https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=600&q=80)`);
        setImageKeywords(detectedProduct.toLowerCase().split(" ").join(", "));
        setUploadImageStep("confirm");
        setIsUploadingImage(false);
      }, 1000);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", uploadImageFile);
      formData.append("product_name", detectedProduct);
      formData.append("description", imageDescription);
      formData.append("price", imagePrice);

      const res = await authenticatedFetch(`/api/agents/${id}/images/upload-and-generate-training`, {
        method: "POST",
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        setDetectedImageId(data.image_id);
        setDetectedImageUrl(data.url);
        setDetectedProduct(data.detected_product || detectedProduct);
        setImageDescription(data.description || imageDescription);
        setImageKeywords(data.keywords || "");
        setSuggestedRule(data.suggested_rule || "");
        setUploadImageStep("confirm");
      } else {
        const data = await res.json();
        alert(`Error al generar entrenamiento: ${data.detail || "Archivo no soportado"}`);
        setUploadImageStep("select");
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al generar el entrenamiento.");
      setUploadImageStep("select");
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleConfirmTraining = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !detectedImageId) return;
    setIsUploadingImage(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        const newImg = {
          id: detectedImageId || `img-${Date.now()}`,
          agent_id: id,
          filename: uploadImageFile?.name || "imagen.png",
          description: imageDescription,
          url: detectedImageUrl,
          uploaded_at: new Date().toISOString()
        };
        setKbImages(prev => [newImg, ...prev]);
        setUploadImageStep("success");
        setUploadImageFile(null);
        setImageDescription("");
        setImagePrice("");
        setDetectedProduct("");
        setSuggestedRule("");
        setImageKeywords("");
        setDetectedImageId(null);
        setDetectedImageUrl("");
        setIsUploadingImage(false);
      }, 500);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/agents/${id}/images/${detectedImageId}/confirm-training`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          description: imageDescription,
          detected_product: detectedProduct,
          keywords: imageKeywords,
          suggested_rule: suggestedRule,
          add_to_prompt: addToPrompt
        })
      });

      if (res.ok) {
        setUploadImageStep("success");
        setUploadImageFile(null);
        setImageDescription("");
        setImagePrice("");
        setDetectedProduct("");
        setSuggestedRule("");
        setImageKeywords("");
        setDetectedImageId(null);
        setDetectedImageUrl("");
        await loadKbImages();
        await loadBackendData();
      } else {
        const data = await res.json();
        alert(`Error al guardar entrenamiento: ${data.detail || "Error interno"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al guardar el entrenamiento.");
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!confirm("¿Deseas eliminar esta imagen de la biblioteca del agente?")) return;

    if (!isBackendOnline) {
      setKbImages(prev => prev.filter(img => img.id !== imageId));
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/images/${imageId}`, { method: "DELETE" });
      if (res.ok) {
        await loadKbImages();
      } else {
        alert("Error al eliminar la imagen.");
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Main Submit (Save Agent)
  const handleSubmitAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveLoading(true);

    const payload = {
      name: form.name,
      description: form.description || null,
      system_prompt: form.system_prompt,
      provider: form.provider,
      model: form.model,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      custom_fields: form.custom_fields,
      channels: form.channels,
      notification_phone: form.notification_phone || null
    };

    if (!isBackendOnline) {
      // Local updates
      alert("💾 Cambios guardados localmente (Mock Mode)");
      setSaveLoading(false);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/agents/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        await loadBackendData();
        alert("💾 Cambios guardados exitosamente.");
      } else {
        const data = await res.json();
        alert(`Error al guardar agente: ${JSON.stringify(data.detail)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al guardar.");
    } finally {
      setSaveLoading(false);
    }
  };

  if (!agent) {
    return (
      <div className="flex h-64 items-center justify-center text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-xs">Cargando agente...</p>
        </div>
      </div>
    );
  }

  // Get active models list based on provider in form
  const currentProviderModels = 
    form.provider === "groq"
      ? availableModels.groq || []
      : form.provider === "gemini"
      ? availableModels.gemini || []
      : availableModels.openrouter || [];

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12 animate-fadeIn text-xs">
      
      {/* Back button */}
      <button
        onClick={() => router.push("/agents")}
        className="flex items-center gap-1 text-gray-400 hover:text-white transition font-semibold cursor-pointer mb-2"
      >
        <ArrowLeft className="w-4 h-4" />
        Volver a Agentes
      </button>

      {/* Title */}
      <div className="flex items-center gap-4 bg-gray-900/10 border border-gray-850 p-6 rounded-2xl">
        <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/15">
          <Bot className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <h3 className="text-md font-bold text-white">Configuración de {agent.name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">Modifica sus instrucciones de sistema, canales y entrenamiento de imágenes.</p>
        </div>
      </div>

      <form onSubmit={handleSubmitAgent} className="space-y-6">

        {/* ── SECCIÓN 1: INFORMACIÓN GENERAL ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("general")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-blue-400" />
              </div>
              <span className="font-bold text-white text-sm">Información General</span>
            </div>
            {expandedSections.general ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          {expandedSections.general && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 space-y-4">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Nombre del Agente *</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={e => setForm(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Descripción</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={e => setForm(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── SECCIÓN 2: PARÁMETROS LLM ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("llm")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-purple-400" />
              </div>
              <span className="font-bold text-white text-sm">Configuración del LLM</span>
            </div>
            {expandedSections.llm ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          {expandedSections.llm && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Proveedor LLM</label>
                <select
                  value={form.provider}
                  onChange={e => handleProviderChange(e.target.value)}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none font-semibold"
                >
                  <option value="groq">Groq (Chat LLM)</option>
                  <option value="gemini">Gemini (Utility LLM)</option>
                  <option value="openrouter">OpenRouter (Multi-LLM)</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Modelo LLM</label>
                <select
                  value={form.model}
                  onChange={e => setForm(prev => ({ ...prev, model: e.target.value }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none font-semibold"
                >
                  {currentProviderModels.map(m => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  {currentProviderModels.length === 0 && (
                    <option value={form.model}>{form.model}</option>
                  )}
                </select>
              </div>
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Temperatura: {form.temperature}</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={form.temperature}
                  onChange={e => setForm(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="w-full accent-blue-500"
                />
              </div>
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Max Tokens</label>
                <input
                  type="number"
                  min="1"
                  max="4096"
                  value={form.max_tokens}
                  onChange={e => setForm(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 1024 }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* ── SECCIÓN 3: PROMPT DEL SISTEMA ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("prompt")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-orange-400" />
              </div>
              <span className="font-bold text-white text-sm">Instrucciones del Sistema (System Prompt)</span>
            </div>
            {expandedSections.prompt ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          {expandedSections.prompt && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 space-y-2">
              <textarea
                required
                rows={8}
                value={form.system_prompt}
                onChange={e => setForm(prev => ({ ...prev, system_prompt: e.target.value }))}
                placeholder="Escribe las instrucciones detalladas de cómo debe actuar el agente..."
                className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-3 text-white focus:outline-none resize-none leading-relaxed font-mono text-[10px]"
              />
              <p className="text-[10px] text-gray-500">Este prompt define la personalidad del agente y las reglas para la recopilación de datos.</p>
            </div>
          )}
        </div>

        {/* ── SECCIÓN 4: CAMPOS PERSONALIZADOS ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("fields")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
                <Database className="w-4 h-4 text-indigo-400" />
              </div>
              <span className="font-bold text-white text-sm">Campos de Captura Personalizados</span>
              <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 text-[10px] rounded-full font-bold">{form.custom_fields.length}</span>
            </div>
            {expandedSections.fields ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          {expandedSections.fields && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 space-y-4">
              
              {/* List of custom fields */}
              <div className="space-y-2">
                {form.custom_fields.map((field: any, idx: number) => (
                  <div key={idx} className={`flex justify-between items-center bg-gray-900/30 border px-4 py-2.5 rounded-xl transition ${editingFieldIndex === idx ? 'border-blue-500/50 shadow-md bg-blue-950/10' : 'border-gray-850'}`}>
                    <div>
                      <span className="font-bold text-blue-400">{field.key}</span>
                      <span className="text-gray-400"> ({field.label})</span>
                      {field.required && <span className="text-red-400 font-bold"> *</span>}
                      {field.description && <p className="text-[10px] text-gray-500 mt-0.5">{field.description}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => startEditCustomField(idx)} className={`hover:text-blue-400 transition ${editingFieldIndex === idx ? 'text-blue-400' : 'text-gray-500'}`} title="Editar campo">
                        <Edit className="w-3.5 h-3.5" />
                      </button>
                      <button type="button" onClick={() => removeCustomField(idx)} className="text-gray-500 hover:text-red-400 transition animate-fadeIn" title="Eliminar campo">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
                {form.custom_fields.length === 0 && (
                  <p className="text-xs text-gray-500 italic py-2 text-center">
                    No has añadido campos (solo se capturarán nombre, email y teléfono por defecto).
                  </p>
                )}
              </div>

              {/* Add / Edit field container */}
              <div className={`p-4 bg-gray-900/10 border rounded-xl space-y-3 transition ${editingFieldIndex !== null ? 'border-blue-500/50 shadow-lg shadow-blue-500/5 bg-blue-950/5' : 'border-gray-850'}`}>
                {editingFieldIndex !== null && (
                  <div className="text-[10px] text-blue-400 font-bold flex items-center gap-1">
                    <Edit className="w-3.5 h-3.5" />
                    Editando campo en posición {editingFieldIndex + 1}
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-gray-400 font-bold mb-1">Nombre técnico (key)</label>
                    <input
                      type="text"
                      value={newField.key}
                      onChange={e => setNewField(prev => ({ ...prev, key: e.target.value.replace(/\s+/g, "_").toLowerCase() }))}
                      placeholder="ej: negocio_tipo"
                      className="w-full bg-[#0c101c] border border-gray-800 rounded-lg px-3 py-1.5 text-white focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 font-bold mb-1">Etiqueta visual (label)</label>
                    <input
                      type="text"
                      value={newField.label}
                      onChange={e => setNewField(prev => ({ ...prev, label: e.target.value }))}
                      placeholder="ej: Tipo de Negocio"
                      className="w-full bg-[#0c101c] border border-gray-800 rounded-lg px-3 py-1.5 text-white focus:outline-none"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
                  <div className="md:col-span-2">
                    <label className="block text-[10px] text-gray-400 font-bold mb-1">Tipo de Dato</label>
                    <select
                      value={newField.type}
                      onChange={e => setNewField(prev => ({ ...prev, type: e.target.value }))}
                      className="w-full bg-[#0c101c] border border-gray-880 rounded-lg px-3 py-1.5 text-white focus:outline-none"
                    >
                      <option value="string">Cadena de Texto</option>
                      <option value="number">Número / Cantidad</option>
                      <option value="boolean">Verdadero / Falso</option>
                    </select>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer mt-4 text-gray-300 font-semibold">
                    <input
                      type="checkbox"
                      checked={newField.required}
                      onChange={e => setNewField(prev => ({ ...prev, required: e.target.checked }))}
                      className="rounded border-gray-800 bg-[#0c101c] text-blue-500 focus:ring-0 w-4 h-4 cursor-pointer"
                    />
                    Requerido
                  </label>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 font-bold mb-1">Descripción instruccional</label>
                  <input
                    type="text"
                    value={newField.description}
                    onChange={e => setNewField(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Instrucción al LLM sobre cómo extraer este dato"
                    className="w-full bg-[#0c101c] border border-gray-880 rounded-lg px-3 py-1.5 text-white focus:outline-none"
                  />
                </div>
                {editingFieldIndex !== null ? (
                  <div className="flex gap-2">
                    <button type="button" onClick={addCustomField} className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-bold transition cursor-pointer">
                      <CheckCircle className="w-3.5 h-3.5" /> Guardar Campo
                    </button>
                    <button type="button" onClick={cancelEditCustomField} className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-gray-800 hover:bg-gray-750 text-gray-300 rounded-lg font-bold transition cursor-pointer">
                      <X className="w-3.5 h-3.5" /> Cancelar
                    </button>
                  </div>
                ) : (
                  <button type="button" onClick={addCustomField} className="w-full flex items-center justify-center gap-1.5 py-2 bg-gray-800 hover:bg-gray-750 text-gray-300 rounded-lg font-bold transition cursor-pointer">
                    <Plus className="w-3.5 h-3.5" /> Añadir Campo
                  </button>
                )}
              </div>

            </div>
          )}
        </div>

        {/* ── SECCIÓN 5: CANALES E INTEGRACIONES ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("channels")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                <Globe className="w-4 h-4 text-cyan-400" />
              </div>
              <span className="font-bold text-white text-sm">Canales de Integración</span>
              <span className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 text-[10px] rounded-full font-bold">{form.channels.length} activo{form.channels.length !== 1 ? "s" : ""}</span>
            </div>
            {expandedSections.channels ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          {expandedSections.channels && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 space-y-4">
              <div>
                <label className="block text-gray-400 font-semibold mb-2">Canales de Comunicación Activos</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { id: "web", label: "Web Chat", icon: <Globe className="w-4 h-4" />, available: true },
                    { id: "whatsapp", label: "WhatsApp", icon: <Phone className="w-4 h-4" />, available: true },
                    { id: "instagram", label: "Instagram DM", icon: <MessageSquare className="w-4 h-4" />, available: false },
                    { id: "telegram", label: "Telegram", icon: <Send className="w-4 h-4" />, available: false },
                  ].map(chan => {
                    const isChecked = form.channels.includes(chan.id);
                    return (
                      <label
                        key={chan.id}
                        className={`relative flex flex-col items-center gap-2 p-3 rounded-xl border cursor-pointer transition-all ${
                          !chan.available 
                            ? 'border-gray-800 bg-gray-900/10 opacity-40 cursor-not-allowed' 
                            : isChecked 
                              ? 'border-blue-500/40 bg-blue-500/5 shadow-sm shadow-blue-500/10' 
                              : 'border-gray-800 bg-gray-900/30 hover:border-gray-750'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          disabled={!chan.available}
                          onChange={() => {
                            if (!chan.available) return;
                            setForm(prev => ({
                              ...prev,
                              channels: isChecked 
                                ? prev.channels.filter((c: string) => c !== chan.id) 
                                : [...prev.channels, chan.id]
                            }));
                          }}
                          className="sr-only"
                        />
                        <div className={`${isChecked ? 'text-blue-400' : 'text-gray-500'}`}>{chan.icon}</div>
                        <span className={`text-[11px] font-medium ${isChecked ? 'text-blue-300' : 'text-gray-400'}`}>{chan.label}</span>
                        {!chan.available && (
                          <span className="absolute top-1 right-1 px-1 py-0.5 bg-amber-500/10 text-amber-400 text-[8px] rounded-full font-bold uppercaseScale">Pronto</span>
                        )}
                        {isChecked && chan.available && (
                          <CheckCircle className="absolute top-1 right-1 w-3.5 h-3.5 text-blue-400" />
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Sub-sección WhatsApp */}
              {form.channels.includes("whatsapp") && (
                <div className="p-4 bg-green-500/5 border border-green-500/20 rounded-xl space-y-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Phone className="w-4 h-4 text-green-400 animate-pulse" />
                    <span className="text-xs font-bold text-green-300">Configuración WhatsApp Cloud API</span>
                    <span className="px-1.5 py-0.5 bg-green-500/10 text-green-400 text-[8px] rounded font-bold uppercase">Activo</span>
                  </div>
                  <div>
                    <label className="block text-gray-400 font-semibold mb-1">Teléfono de Notificaciones (encargado)</label>
                    <input
                      type="text"
                      value={form.notification_phone}
                      onChange={e => setForm(prev => ({ ...prev, notification_phone: e.target.value }))}
                      placeholder="Ej: +573001234567"
                      className="w-full bg-[#0c101c] border border-gray-800 focus:border-green-500 rounded-xl px-4 py-2 text-white focus:outline-none text-sm"
                    />
                    <p className="text-[10px] text-gray-500 mt-1">El encargado recibirá notificaciones automáticas de leads capturados.</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── SECCIÓN 6: ENTRENAMIENTO VISUAL ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("visual")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-yellow-400" />
              </div>
              <span className="font-bold text-white text-sm">Entrenamiento Visual (Visión Artificial)</span>
              <span className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 text-[10px] rounded-full font-bold">{kbImages.length} imagen{kbImages.length !== 1 ? "es" : ""}</span>
            </div>
            {expandedSections.visual ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>
          
          {expandedSections.visual && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Upload Form (1 col) */}
                <div className="bg-[#0c101c]/40 border border-gray-850 p-5 rounded-2xl h-fit">
                  <h4 className="font-bold text-white text-xs mb-3 flex items-center gap-1.5">
                    <Upload className="w-4 h-4 text-blue-400" />
                    Subir y Entrenar Imagen
                  </h4>

                  {uploadImageStep === "select" && (
                    <form onSubmit={handleUploadAndGenerateTraining} className="space-y-4">
                      {/* Image Dropzone */}
                      <div className="relative border-2 border-dashed border-gray-850 hover:border-blue-500/30 rounded-xl p-4 flex flex-col items-center justify-center gap-2 cursor-pointer text-center hover:bg-blue-500/5 transition">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={e => {
                            if (e.target.files?.[0]) {
                              setUploadImageFile(e.target.files[0]);
                              // Autopopulate detected product with name from file if empty
                              if (!detectedProduct) {
                                setDetectedProduct(e.target.files[0].name.split(".")[0].replace(/[_-]/g, " "));
                              }
                            }
                          }}
                          className="absolute inset-0 opacity-0 cursor-pointer"
                        />
                        <Upload className="w-6 h-6 text-gray-500" />
                        <span className="text-[11px] text-gray-400 font-semibold">
                          {uploadImageFile ? uploadImageFile.name : "Seleccionar Imagen del Producto"}
                        </span>
                        <span className="text-[9px] text-gray-500">JPG, PNG o WEBP (máx. 5MB)</span>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Nombre del producto o espacio</label>
                          <input
                            type="text"
                            required
                            placeholder="Ej. Sala de Juntas VIP"
                            value={detectedProduct}
                            onChange={e => setDetectedProduct(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Precio</label>
                          <input
                            type="text"
                            required
                            placeholder="Ej. $50.000 COP/hora o Gratis"
                            value={imagePrice}
                            onChange={e => setImagePrice(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Descripción detallada</label>
                          <textarea
                            required
                            rows={3}
                            placeholder="Ej. Espacio privado con capacidad para 10 personas, aire acondicionado..."
                            value={imageDescription}
                            onChange={e => setImageDescription(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none resize-none leading-relaxed"
                          />
                        </div>
                      </div>

                      <button
                        type="submit"
                        disabled={!uploadImageFile || !detectedProduct || !imageDescription || !imagePrice || isUploadingImage}
                        className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                      >
                        <Sparkles className="w-4 h-4 text-yellow-350" />
                        Subir y Entrenar con IA
                      </button>
                    </form>
                  )}

                  {uploadImageStep === "analyzing" && (
                    <div className="py-8 text-center space-y-4">
                      <div className="relative w-12 h-12 mx-auto flex items-center justify-center">
                        <Loader2 className="w-12 h-12 text-blue-500 animate-spin absolute" />
                        <Sparkles className="w-5 h-5 text-yellow-400 animate-pulse" />
                      </div>
                      <div className="space-y-1">
                        <p className="font-bold text-gray-200 text-[11px]">🧠 Analizando con IA...</p>
                        <p className="text-[9px] text-gray-500 leading-relaxed max-w-[90%] mx-auto">
                          Genia está analizando la imagen para estructurar las reglas de visualización y prompt.
                        </p>
                      </div>
                    </div>
                  )}

                  {uploadImageStep === "confirm" && (
                    <form onSubmit={handleConfirmTraining} className="space-y-4">
                      <div className="bg-[#070b13] border border-gray-850 rounded-xl p-3 flex gap-3 items-center">
                        {detectedImageUrl && (
                          <img
                            src={detectedImageUrl}
                            alt="Preview"
                            className="w-12 h-12 object-cover rounded-lg border border-gray-750"
                          />
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="font-bold text-gray-200 truncate">{uploadImageFile?.name || "imagen.png"}</p>
                          <span className="text-[8px] px-1.5 py-0.5 bg-blue-950 text-blue-400 border border-blue-900 rounded font-semibold">
                            Análisis Listo ✨
                          </span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Nombre Ajustado</label>
                          <input
                            type="text"
                            required
                            value={detectedProduct}
                            onChange={e => setDetectedProduct(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Descripción del Agente</label>
                          <textarea
                            required
                            value={imageDescription}
                            onChange={e => setImageDescription(e.target.value)}
                            rows={3}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none resize-none leading-relaxed"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Palabras Clave (ej. gatillos)</label>
                          <input
                            type="text"
                            required
                            value={imageKeywords}
                            onChange={e => setImageKeywords(e.target.value)}
                            placeholder="ej: sala juntas, fotos sala, precio sala"
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Instrucción para el Prompt</label>
                          <textarea
                            required
                            value={suggestedRule}
                            onChange={e => setSuggestedRule(e.target.value)}
                            rows={4}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white font-mono text-[9px] focus:outline-none resize-none leading-relaxed"
                          />
                        </div>

                        <div className="flex items-center gap-2 pt-1">
                          <input
                            type="checkbox"
                            id="addToPrompt"
                            checked={addToPrompt}
                            onChange={e => setAddToPrompt(e.target.checked)}
                            className="rounded border-gray-850 bg-[#070b13] text-blue-600 focus:ring-0 w-4 h-4 cursor-pointer"
                          />
                          <label htmlFor="addToPrompt" className="text-gray-300 font-semibold select-none cursor-pointer">
                            Actualizar prompt automáticamente
                          </label>
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setUploadImageStep("select");
                            setUploadImageFile(null);
                            setImageDescription("");
                            setImagePrice("");
                            setDetectedProduct("");
                          }}
                          className="flex-1 py-2 bg-gray-850 hover:bg-gray-800 border border-gray-700 text-gray-300 rounded-xl font-bold transition text-center cursor-pointer"
                        >
                          Cancelar
                        </button>
                        <button
                          type="submit"
                          className="flex-1 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                        >
                          Entrenar
                        </button>
                      </div>
                    </form>
                  )}

                  {uploadImageStep === "success" && (
                    <div className="py-6 text-center space-y-4">
                      <div className="w-10 h-10 bg-green-950/30 border border-green-500/20 text-green-400 rounded-full flex items-center justify-center mx-auto animate-bounce">
                        <CheckCircle className="w-5 h-5" />
                      </div>
                      <div className="space-y-1">
                        <p className="font-bold text-gray-200 text-xs">¡Entrenado!</p>
                        <p className="text-[9px] text-gray-500 leading-relaxed max-w-[90%] mx-auto">
                          El agente ha aprendido sobre la imagen y su Prompt se ha actualizado.
                        </p>
                      </div>
                      <button
                        onClick={() => setUploadImageStep("select")}
                        className="py-1.5 px-4 bg-blue-950/40 hover:bg-blue-900/40 border border-blue-500/20 text-blue-400 rounded-xl text-[10px] font-bold transition mx-auto block cursor-pointer"
                      >
                        Entrenar Otra
                      </button>
                    </div>
                  )}

                </div>

                {/* Image Gallery (2 cols) */}
                <div className="md:col-span-2 space-y-4">
                  <h4 className="font-bold text-white text-xs">Galería de Imágenes Entrenadas</h4>
                  
                  {kbImagesLoading ? (
                    <div className="flex h-36 items-center justify-center">
                      <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {kbImages.map((img) => (
                        <div key={img.id} className="glow-card rounded-2xl overflow-hidden flex flex-col justify-between bg-gray-900/10 border border-gray-850">
                          <div className="relative aspect-video bg-black/40 border-b border-gray-850">
                            <img src={img.url} alt={img.filename} className="w-full h-full object-cover" />
                          </div>
                          <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                            <div>
                              <h5 className="font-bold text-gray-200 text-xs truncate" title={img.filename}>
                                {img.filename}
                              </h5>
                              <p className="text-[10px] text-gray-400 mt-1 line-clamp-3 italic leading-relaxed">
                                "{img.description}"
                              </p>
                            </div>
                            <div className="flex items-center justify-between border-t border-gray-850/40 pt-2">
                              <span className="text-[8px] text-gray-500 font-mono">
                                {new Date(img.uploaded_at).toLocaleDateString()}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleDeleteImage(img.id)}
                                className="p-1.5 bg-red-950/20 hover:bg-red-900/30 text-red-400 rounded-lg border border-red-500/10 hover:border-red-500/20 transition cursor-pointer"
                                title="Eliminar Imagen"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                      {kbImages.length === 0 && (
                        <div className="col-span-2 py-12 text-center text-gray-500 border border-dashed border-gray-850 rounded-2xl">
                          <FolderOpen className="w-8 h-8 mx-auto text-gray-650 mb-2" />
                          <p className="font-semibold text-xs">No hay imágenes en la biblioteca</p>
                          <p className="text-[10px] text-gray-550 mt-0.5">Usa el formulario de la izquierda para entrenar imágenes explicativas.</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

              </div>
            </div>
          )}
        </div>

        {/* ── BOTÓN DE GUARDAR GLOBAL ── */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={saveLoading}
            className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg shadow-blue-500/15 hover:shadow-blue-500/25 transition-all text-xs flex items-center justify-center gap-1.5 cursor-pointer"
          >
            {saveLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              "💾 Guardar Configuración del Agente"
            )}
          </button>
        </div>

      </form>
    </div>
  );
}
