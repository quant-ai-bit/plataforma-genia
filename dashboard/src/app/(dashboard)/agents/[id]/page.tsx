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
  Upload,
  Eye,
  EyeOff,
  Copy,
  Check,
  RefreshCw
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
    notification_phone: "",
    stt_provider: "groq_whisper",
    timezone: "America/Bogota",
    google_calendar_client_id: "",
    google_calendar_client_secret: ""
  });

  // Collapsible Sections
  const [expandedSections, setExpandedSections] = useState({
    general: true,
    llm: true,
    prompt: true,
    fields: true,
    channels: true,
    calendar: true,
    advanced: false,
    visual: true
  });

  // Google Calendar Integration State
  const [calStatus, setCalStatus] = useState<{
    connected: boolean;
    email: string | null;
  } | null>(null);
  const [calStatusLoading, setCalStatusLoading] = useState<boolean>(false);
  const [calDisconnecting, setCalDisconnecting] = useState<boolean>(false);
  const [calEvents, setCalEvents] = useState<any[]>([]);
  const [calEventsLoading, setCalEventsLoading] = useState<boolean>(false);
  const [showCalSecrets, setShowCalSecrets] = useState<boolean>(false);

  // Custom Fields Editing State
  const [newField, setNewField] = useState({
    key: "",
    label: "",
    type: "string",
    required: false,
    description: ""
  });
  const [editingFieldIndex, setEditingFieldIndex] = useState<number | null>(null);

  // WhatsApp Integration State
  const [waStatus, setWaStatus] = useState<{
    connected: boolean;
    phone_number_id: string | null;
    phone_number: string | null;
    display_name: string | null;
    webhook_url: string | null;
    verify_token: string | null;
    whatsapp_provider?: string;
    whatsapp_qr_connected?: boolean;
    whatsapp_qr_instance_name?: string | null;
    qr_code?: string | null;
    is_mock_mode?: boolean;
    error?: string;
  } | null>(null);
  const [waStatusLoading, setWaStatusLoading] = useState<boolean>(false);
  const [waConnecting, setWaConnecting] = useState<boolean>(false);
  const [waDisconnecting, setWaDisconnecting] = useState<boolean>(false);
  const [waQrRequested, setWaQrRequested] = useState<boolean>(false);
  const [showWaSecrets, setShowWaSecrets] = useState<boolean>(false);
  const [copiedWebhook, setCopiedWebhook] = useState<boolean>(false);
  const [copiedToken, setCopiedToken] = useState<boolean>(false);
  const [waForm, setWaForm] = useState({
    phone_number_id: "",
    access_token: "",
    app_secret: "",
    verify_token: `genia_verify_${id ? id.split("-")[0] : "token"}`
  });

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
        notification_phone: foundAgent.notification_phone || "",
        stt_provider: foundAgent.stt_provider || "groq_whisper",
        timezone: foundAgent.timezone || "America/Bogota",
        google_calendar_client_id: foundAgent.google_calendar_client_id || "",
        google_calendar_client_secret: ""
      });
    }
  }, [id, agents]);

  useEffect(() => {
    if (id) {
      loadKbImages();
      fetchWhatsAppStatus();
      fetchCalendarStatus();
    }
  }, [id, isBackendOnline]);

  // Polling para WhatsApp QR (WAHA y QR Code)
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (
      (waStatus?.whatsapp_provider === "waha" || waStatus?.whatsapp_provider === "qr_code") &&
      !waStatus.connected &&
      (waStatus.whatsapp_qr_instance_name || waQrRequested)
    ) {
      interval = setInterval(() => {
        fetchWhatsAppStatus();
      }, 5000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [waStatus?.whatsapp_provider, waStatus?.connected, waStatus?.whatsapp_qr_instance_name, waQrRequested]);

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

  const fetchWhatsAppStatus = async () => {
    if (!id) return;
    if (!isBackendOnline) {
      setWaStatus({
        connected: false,
        phone_number_id: null,
        phone_number: null,
        display_name: null,
        webhook_url: "/api/whatsapp/webhook",
        verify_token: `genia_verify_${id.split("-")[0]}`
      });
      return;
    }
    setWaStatusLoading(true);
    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/status`);
      if (res.ok) {
        const data = await res.json();
        setWaStatus(data);
        if (data.verify_token) {
          setWaForm(prev => ({
            ...prev,
            verify_token: data.verify_token
          }));
        } else {
          setWaForm(prev => ({
            ...prev,
            verify_token: `genia_verify_${id.split("-")[0]}`
          }));
        }
        if (data.phone_number_id) {
          setWaForm(prev => ({
            ...prev,
            phone_number_id: data.phone_number_id
          }));
        }
      }
    } catch (err) {
      console.error("Error al obtener estado de WhatsApp:", err);
    } finally {
      setWaStatusLoading(false);
    }
  };

  const fetchCalendarStatus = async () => {
    if (!id) return;
    if (!isBackendOnline) {
      setCalStatus({
        connected: false,
        email: null
      });
      return;
    }
    setCalStatusLoading(true);
    try {
      const res = await authenticatedFetch(`/api/calendar/${id}/status`);
      if (res.ok) {
        const data = await res.json();
        setCalStatus(data);
        if (data.connected) {
          fetchCalendarEvents();
        }
      }
    } catch (err) {
      console.error("Error al obtener estado de Calendar:", err);
    } finally {
      setCalStatusLoading(false);
    }
  };

  const fetchCalendarEvents = async () => {
    if (!id) return;
    if (!isBackendOnline) return;
    setCalEventsLoading(true);
    try {
      const res = await authenticatedFetch(`/api/calendar/${id}/events?days=7`);
      if (res.ok) {
        const data = await res.json();
        setCalEvents(data.events || []);
      }
    } catch (err) {
      console.error("Error al obtener eventos de Calendar:", err);
    } finally {
      setCalEventsLoading(false);
    }
  };

  const handleDisconnectCalendar = async () => {
    if (!confirm("¿Estás seguro de que deseas desconectar Google Calendar?")) return;
    setCalDisconnecting(true);
    try {
      const res = await authenticatedFetch(`/api/calendar/${id}/disconnect`, {
        method: "POST"
      });
      if (res.ok) {
        alert("📅 Google Calendar desconectado exitosamente.");
        setCalStatus({ connected: false, email: null });
        setCalEvents([]);
        await loadBackendData();
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al desconectar Calendar.");
    } finally {
      setCalDisconnecting(false);
    }
  };

  const handleConnectCalendar = async () => {
    if (!form.google_calendar_client_id.trim()) {
      alert("Por favor, ingresa el Client ID de Google para iniciar la conexión.");
      return;
    }
    
    setSaveLoading(true);
    try {
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
        notification_phone: form.notification_phone || null,
        stt_provider: form.stt_provider,
        timezone: form.timezone,
        google_calendar_client_id: form.google_calendar_client_id,
        google_calendar_client_secret: form.google_calendar_client_secret || null
      };

      const res = await authenticatedFetch(`/api/agents/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        alert("Error al guardar credenciales antes de conectar.");
        setSaveLoading(false);
        return;
      }
    } catch (err) {
      console.error(err);
      alert("Error guardando credenciales.");
      setSaveLoading(false);
      return;
    } finally {
      setSaveLoading(false);
    }

    try {
      const origin = window.location.origin;
      const res = await authenticatedFetch(`/api/calendar/${id}/auth-url?base_url=${encodeURIComponent(origin)}`);
      if (res.ok) {
        const data = await res.json();
        const width = 600, height = 650;
        const left = (window.innerWidth - width) / 2;
        const top = (window.innerHeight - height) / 2;
        const popup = window.open(
          data.auth_url,
          "Google Calendar Authorization",
          `width=${width},height=${height},left=${left},top=${top}`
        );

        const handleMessage = async (event: MessageEvent) => {
          if (event.data && event.data.type === 'calendar_connected') {
            alert(`📅 Calendario conectado con éxito: ${event.data.email}`);
            await fetchCalendarStatus();
            await loadBackendData();
            window.removeEventListener('message', handleMessage);
          }
        };
        window.addEventListener('message', handleMessage);
      } else {
        const data = await res.json();
        alert(`Error al iniciar conexión: ${data.detail || "Verifica las credenciales."}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error al intentar conectar.");
    }
  };

  const handleConnectWhatsApp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!waForm.phone_number_id.trim() || !waForm.access_token.trim() || !waForm.app_secret.trim()) {
      alert("Por favor, completa todos los campos requeridos para la conexión.");
      return;
    }
    setWaConnecting(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: true,
          phone_number_id: waForm.phone_number_id,
          phone_number: "+573001234567",
          display_name: "Línea de Prueba Genia",
          webhook_url: "/api/whatsapp/webhook",
          verify_token: waForm.verify_token || `genia_verify_${id.split("-")[0]}`
        });
        setForm(prev => ({
          ...prev,
          channels: prev.channels.includes("whatsapp") ? prev.channels : [...prev.channels, "whatsapp"]
        }));
        alert("🔌 WhatsApp conectado en modo simulación (Mock)");
        setWaConnecting(false);
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(waForm)
      });

      if (res.ok) {
        alert("🔌 WhatsApp conectado exitosamente.");
        setWaForm(prev => ({ ...prev, access_token: "", app_secret: "" }));
        await fetchWhatsAppStatus();
        await loadBackendData();
      } else {
        const data = await res.json();
        alert(`Error al conectar WhatsApp: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al conectar con el backend.");
    } finally {
      setWaConnecting(false);
    }
  };

  const handleDisconnectWhatsApp = async () => {
    if (!confirm("¿Estás seguro de que deseas desconectar WhatsApp de este agente? Se eliminarán las credenciales de Meta asociadas.")) return;
    setWaDisconnecting(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: false,
          phone_number_id: null,
          phone_number: null,
          display_name: null,
          webhook_url: "/api/whatsapp/webhook",
          verify_token: `genia_verify_${id.split("-")[0]}`
        });
        setWaDisconnecting(false);
        alert("🔌 WhatsApp desconectado en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/disconnect`, {
        method: "POST"
      });

      if (res.ok) {
        alert("🔌 WhatsApp desconectado exitosamente.");
        await fetchWhatsAppStatus();
        await loadBackendData();
      } else {
        const data = await res.json();
        alert(`Error al desconectar WhatsApp: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al desconectar.");
    } finally {
      setWaDisconnecting(false);
    }
  };

  const handleConnectWhatsAppQR = async () => {
    setWaConnecting(true);
    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: false,
          phone_number_id: null,
          phone_number: null,
          display_name: null,
          webhook_url: `/api/whatsapp/webhook/qr/${id}`,
          verify_token: `genia_verify_${id.split("-")[0]}`,
          whatsapp_provider: "qr_code",
          whatsapp_qr_connected: false,
          whatsapp_qr_instance_name: `genia_agent_${id}`,
          qr_code: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwABg4m4AAAAASUVORK5CYII=",
          is_mock_mode: true
        });
        setForm(prev => ({
          ...prev,
          channels: prev.channels.includes("whatsapp") ? prev.channels : [...prev.channels, "whatsapp"]
        }));
        setWaConnecting(false);
        alert("🔌 Instancia QR generada en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/qr/connect`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        // Cargar el estado actualizado del servidor
        await fetchWhatsAppStatus();
        // Si el endpoint devolvió el QR directamente, aplicarlo al estado para mostrarlo de inmediato
        if (data.qr_code) {
          setWaStatus(prev => prev ? { ...prev, qr_code: data.qr_code } : prev);
        }
        alert("🔌 Instancia QR generada. Por favor escanea el código QR.");
      } else {
        const data = await res.json();
        alert(`Error al generar código QR: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al generar QR.");
    } finally {
      setWaConnecting(false);
    }
  };

  const handleDisconnectWhatsAppQR = async () => {
    if (!confirm("¿Estás seguro de que deseas desconectar WhatsApp QR de este agente?")) return;
    setWaDisconnecting(true);

    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: false,
          phone_number_id: null,
          phone_number: null,
          display_name: null,
          webhook_url: "/api/whatsapp/webhook",
          verify_token: `genia_verify_${id.split("-")[0]}`,
          whatsapp_provider: "meta_cloud",
          whatsapp_qr_connected: false,
          whatsapp_qr_instance_name: null,
          qr_code: null
        });
        setWaDisconnecting(false);
        alert("🔌 WhatsApp QR desconectado en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/qr/disconnect`, {
        method: "POST"
      });
      if (res.ok) {
        alert("🔌 WhatsApp QR desconectado exitosamente.");
        await fetchWhatsAppStatus();
        await loadBackendData();
      } else {
        const data = await res.json();
        alert(`Error al desconectar WhatsApp QR: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al desconectar QR.");
    } finally {
      setWaDisconnecting(false);
    }
  };

  const handleConnectWhatsAppWaha = async () => {
    setWaConnecting(true);
    setWaQrRequested(true);
    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: false,
          phone_number_id: null,
          phone_number: null,
          display_name: null,
          webhook_url: `/api/whatsapp/webhook/waha/${id}`,
          verify_token: `genia_verify_${id.split("-")[0]}`,
          whatsapp_provider: "waha",
          whatsapp_qr_connected: false,
          whatsapp_qr_instance_name: `genia_waha_${id}`,
          qr_code: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwABg4m4AAAAASUVORK5CYII=",
          is_mock_mode: true
        });
        setForm(prev => ({
          ...prev,
          channels: prev.channels.includes("whatsapp") ? prev.channels : [...prev.channels, "whatsapp"]
        }));
        setWaConnecting(false);
        alert("🔌 Sesión WAHA generada en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/waha/connect`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        if (data.qr_code) {
          setWaStatus(prev => prev ? { ...prev, qr_code: data.qr_code } : prev);
        }
        await fetchWhatsAppStatus();
        alert("🔌 Sesión WAHA generada. Por favor escanea el código QR.");
      } else {
        const data = await res.json();
        alert(`Error al generar código QR WAHA: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al generar QR WAHA.");
    } finally {
      setWaConnecting(false);
    }
  };

  const handleDisconnectWhatsAppWaha = async () => {
    if (!confirm("¿Estás seguro de que deseas desconectar WhatsApp WAHA de este agente?")) return;
    setWaDisconnecting(true);
    setWaQrRequested(false);

    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus({
          connected: false,
          phone_number_id: null,
          phone_number: null,
          display_name: null,
          webhook_url: "/api/whatsapp/webhook",
          verify_token: `genia_verify_${id.split("-")[0]}`,
          whatsapp_provider: "meta_cloud",
          whatsapp_qr_connected: false,
          whatsapp_qr_instance_name: null,
          qr_code: null
        });
        setWaDisconnecting(false);
        alert("🔌 WhatsApp WAHA desconectado en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/waha/disconnect`, {
        method: "POST"
      });
      if (res.ok) {
        alert("🔌 WhatsApp WAHA desconectado exitosamente.");
        await fetchWhatsAppStatus();
        await loadBackendData();
      } else {
        const data = await res.json();
        alert(`Error al desconectar WhatsApp WAHA: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al desconectar WAHA.");
    } finally {
      setWaDisconnecting(false);
    }
  };

  const handleRestartWhatsAppWaha = async () => {
    setWaConnecting(true);
    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus(prev => prev ? {
          ...prev,
          qr_code: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwABg4m4AAAAASUVORK5CYII=",
          connected: false,
          whatsapp_qr_connected: false
        } : null);
        setWaConnecting(false);
        alert("🔌 Sesión WAHA reiniciada en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/waha/restart`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        if (data.qr_code) {
          setWaStatus(prev => prev ? { ...prev, qr_code: data.qr_code, connected: false } : prev);
        }
        await fetchWhatsAppStatus();
        alert("🔌 Sesión WAHA reiniciada. Escanea el nuevo código QR.");
      } else {
        const data = await res.json();
        alert(`Error al reiniciar WAHA: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al reiniciar WAHA.");
    } finally {
      setWaConnecting(false);
    }
  };

  const handleRestartWhatsAppQR = async () => {
    setWaConnecting(true);
    if (!isBackendOnline) {
      setTimeout(() => {
        setWaStatus(prev => prev ? {
          ...prev,
          qr_code: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJQAAACUAQMAAABvMD4ZAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAAlwSFlzAAAOxAAADsQBlbZJywAAABpJREFUeNpiYGBgYGBgYGBgYGBgYGBgYGBgYADADAADwABg4m4AAAAASUVORK5CYII=",
          connected: false,
          whatsapp_qr_connected: false
        } : null);
        setWaConnecting(false);
        alert("🔌 Instancia QR reiniciada en modo simulación (Mock)");
      }, 1000);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/qr/restart`, {
        method: "POST"
      });
      if (res.ok) {
        const data = await res.json();
        await fetchWhatsAppStatus();
        if (data.qr_code) {
          setWaStatus(prev => prev ? { ...prev, qr_code: data.qr_code, connected: false } : prev);
        }
        alert("🔌 Instancia QR reiniciada. Escanea el nuevo código QR.");
      } else {
        const data = await res.json();
        alert(`Error al reiniciar QR: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión al reiniciar QR.");
    } finally {
      setWaConnecting(false);
    }
  };

  const handleSimulateScanWaha = async () => {
    if (!isBackendOnline) {
      setWaStatus(prev => prev ? {
        ...prev,
        connected: true,
        whatsapp_qr_connected: true,
        phone_number: "573103125460",
        display_name: "Línea WAHA Simulada"
      } : null);
      alert("🔌 Escaneo de QR WAHA simulado exitosamente en modo local.");
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/waha/simulate-scan`, {
        method: "POST"
      });
      if (res.ok) {
        await fetchWhatsAppStatus();
        alert("🔌 Escaneo de QR WAHA simulado exitosamente.");
      } else {
        const data = await res.json();
        alert(`Error al simular escaneo WAHA: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión con el backend.");
    }
  };

  const handleSimulateScanQR = async () => {
    if (!isBackendOnline) {
      setWaStatus(prev => prev ? {
        ...prev,
        connected: true,
        whatsapp_qr_connected: true,
        phone_number: "573103125460",
        display_name: "Línea QR Simulada"
      } : null);
      alert("🔌 Escaneo de QR simulado exitosamente en modo local.");
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/qr/simulate-scan`, {
        method: "POST"
      });
      if (res.ok) {
        await fetchWhatsAppStatus();
        alert("🔌 Escaneo de QR simulado exitosamente.");
      } else {
        const data = await res.json();
        alert(`Error al simular escaneo: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
      alert("Error de conexión con el backend.");
    }
  };

  const changeWhatsAppProvider = async (provider: "meta_cloud" | "qr_code" | "waha") => {
    if (!isBackendOnline) {
      setWaStatus(prev => prev ? { ...prev, whatsapp_provider: provider } : null);
      return;
    }

    try {
      const res = await authenticatedFetch(`/api/whatsapp/${id}/provider`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider })
      });
      if (res.ok) {
        await fetchWhatsAppStatus();
      } else {
        const data = await res.json();
        alert(`Error al cambiar de proveedor: ${data.detail || JSON.stringify(data)}`);
      }
    } catch (err) {
      console.error(err);
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
  const handleUploadAndGenerateTraining = async (e?: React.FormEvent | React.MouseEvent) => {
    if (e) e.preventDefault();
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

  const handleConfirmTraining = async (e?: React.FormEvent | React.MouseEvent) => {
    if (e) e.preventDefault();
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
      notification_phone: form.notification_phone || null,
      stt_provider: form.stt_provider,
      timezone: form.timezone,
      google_calendar_client_id: form.google_calendar_client_id || null,
      google_calendar_client_secret: form.google_calendar_client_secret || null
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
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Proveedor de Notas de Voz (STT)</label>
                <select
                  value={form.stt_provider}
                  onChange={e => setForm(prev => ({ ...prev, stt_provider: e.target.value }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none font-semibold"
                >
                  <option value="groq_whisper">Groq Whisper (Recomendado - Español)</option>
                  <option value="openai_whisper">OpenAI Whisper API</option>
                  <option value="deepgram">Deepgram Nova-3 (Baja Latencia)</option>
                  <option value="google_stt">Google Cloud Speech-to-Text</option>
                </select>
              </div>
              <div>
                <label className="block text-gray-400 font-semibold mb-1">Zona Horaria del Negocio</label>
                <select
                  value={form.timezone}
                  onChange={e => setForm(prev => ({ ...prev, timezone: e.target.value }))}
                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-blue-500 rounded-xl px-4 py-2 text-white focus:outline-none font-semibold"
                >
                  <option value="America/Bogota">Colombia (UTC-5 - Por Defecto)</option>
                  <option value="America/Mexico_City">México (UTC-6)</option>
                  <option value="America/Lima">Perú (UTC-5)</option>
                  <option value="America/Caracas">Venezuela (UTC-4)</option>
                  <option value="America/Santiago">Chile (UTC-3)</option>
                  <option value="America/Argentina/Buenos_Aires">Argentina (UTC-3)</option>
                  <option value="America/New_York">Estados Unidos EST (UTC-5)</option>
                  <option value="America/Los_Angeles">Estados Unidos PST (UTC-8)</option>
                  <option value="Europe/Madrid">España (UTC+1)</option>
                </select>
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
                <div className="p-6 bg-[#0e1324]/80 border border-green-500/10 rounded-2xl space-y-6 backdrop-blur-md shadow-lg shadow-green-500/5 transition-all">
                  
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-gray-800">
                    <div className="flex items-center gap-2">
                      <Phone className="w-5 h-5 text-green-400 animate-pulse" />
                      <div>
                        <span className="text-sm font-bold text-white block">Integración de WhatsApp</span>
                        <span className="text-[10px] text-gray-400">Elige cómo vincular el agente con la línea de WhatsApp</span>
                      </div>
                    </div>

                    {/* Tabs de Proveedor */}
                    <div className="flex bg-[#070b16] p-1 rounded-xl border border-gray-800">
                      <button
                        type="button"
                        onClick={() => changeWhatsAppProvider("meta_cloud")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          (waStatus?.whatsapp_provider || "meta_cloud") === "meta_cloud"
                            ? "bg-green-500/20 text-green-400 border border-green-500/20"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Oficial (Meta API)
                      </button>
                      <button
                        type="button"
                        onClick={() => changeWhatsAppProvider("qr_code")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          waStatus?.whatsapp_provider === "qr_code"
                            ? "bg-green-500/20 text-green-400 border border-green-500/20"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Código QR (Baileys)
                      </button>
                      <button
                        type="button"
                        onClick={() => changeWhatsAppProvider("waha")}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                          waStatus?.whatsapp_provider === "waha"
                            ? "bg-green-500/20 text-green-400 border border-green-500/20"
                            : "text-gray-400 hover:text-white"
                        }`}
                      >
                        Código QR (WAHA)
                      </button>
                    </div>

                    {/* Estado de Conexión */}
                    {waStatusLoading ? (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-800/40 text-gray-400 text-[10px] rounded-full">
                        <Loader2 className="w-3 h-3 animate-spin text-green-400" />
                        <span>Verificando...</span>
                      </div>
                    ) : waStatus?.connected ? (
                      <span className="px-2.5 py-1 bg-green-500/10 text-green-400 border border-green-500/20 text-[10px] rounded-full font-bold uppercase tracking-wider flex items-center gap-1 self-start sm:self-auto">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-ping"></span>
                        Conectado
                      </span>
                    ) : (
                      <span className="px-2.5 py-1 bg-gray-800 text-gray-400 border border-gray-700 text-[10px] rounded-full font-bold uppercase tracking-wider self-start sm:self-auto">
                        Desconectado
                      </span>
                    )}
                  </div>

                  {/* Notification Phone (Human Backup) - Always visible */}
                  <div className="bg-[#070b16]/60 p-4 border border-gray-850 rounded-xl space-y-2">
                    <label className="block text-gray-300 font-semibold text-xs">Teléfono del Encargado (Notificaciones de Leads)</label>
                    <input
                      type="text"
                      value={form.notification_phone || ""}
                      onChange={e => setForm(prev => ({ ...prev, notification_phone: e.target.value }))}
                      placeholder="Ej: +573001234567"
                      className="w-full bg-[#0c101c] border border-gray-850 focus:border-green-500 rounded-xl px-4 py-2 text-white focus:outline-none text-sm transition-all focus:ring-1 focus:ring-green-500"
                    />
                    <p className="text-[10px] text-gray-500">
                      Este número recibirá alertas de WhatsApp cuando un lead requiera atención humana (Handoff) o termine su flujo.
                    </p>
                  </div>

                  {/* VISTA 1: Proveedor META CLOUD API */}
                  {(waStatus?.whatsapp_provider || "meta_cloud") === "meta_cloud" && (
                    <div className="space-y-5">
                      {waStatus?.connected ? (
                        <div className="space-y-4">
                          {/* Detalles del número oficial */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-green-500/[0.02] p-4 border border-green-500/10 rounded-xl">
                            <div>
                              <span className="text-gray-400 text-[10px] block">Nombre de la Línea (Meta)</span>
                              <span className="text-white text-xs font-semibold">{waStatus.display_name || 'No disponible'}</span>
                            </div>
                            <div>
                              <span className="text-gray-400 text-[10px] block">Número Telefónico</span>
                              <span className="text-white text-xs font-semibold">{waStatus.phone_number || 'No disponible'}</span>
                            </div>
                            <div className="md:col-span-2">
                              <span className="text-gray-400 text-[10px] block">Phone Number ID</span>
                              <span className="font-mono text-gray-300 text-xs">{waStatus.phone_number_id}</span>
                            </div>
                          </div>

                          {/* Callback URLs */}
                          <div className="bg-[#070b16]/60 p-4 border border-gray-850 rounded-xl space-y-3">
                            <span className="text-xs font-bold text-blue-400 block">Configuración de Webhook en Meta</span>
                            <p className="text-[10px] text-gray-400 leading-relaxed">
                              Configura el webhook en tu aplicación de Meta Developers con los siguientes datos:
                            </p>
                            
                            <div className="space-y-2 text-xs">
                              <div>
                                <span className="text-gray-400 text-[10px] block mb-1">URL de la Rellamada (Callback URL)</span>
                                <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-lg p-2 font-mono">
                                  <span className="text-gray-300 truncate flex-1 text-[11px]">
                                    {typeof window !== "undefined" ? `${window.location.origin}${waStatus.webhook_url}` : `https://plataforma.genia.com.co${waStatus.webhook_url}`}
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const url = typeof window !== "undefined" ? `${window.location.origin}${waStatus.webhook_url}` : `https://plataforma.genia.com.co${waStatus.webhook_url}`;
                                      navigator.clipboard.writeText(url);
                                      setCopiedWebhook(true);
                                      setTimeout(() => setCopiedWebhook(false), 2000);
                                    }}
                                    className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800 transition"
                                  >
                                    {copiedWebhook ? <CheckCircle className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                                  </button>
                                </div>
                              </div>

                              <div>
                                <span className="text-gray-400 text-[10px] block mb-1">Token de Verificación (Verify Token)</span>
                                <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-lg p-2 font-mono">
                                  <span className="text-gray-300 truncate flex-1 text-[11px]">
                                    {waStatus.verify_token || "Token no configurado"}
                                  </span>
                                  {waStatus.verify_token && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        navigator.clipboard.writeText(waStatus.verify_token || "");
                                        setCopiedToken(true);
                                        setTimeout(() => setCopiedToken(false), 2000);
                                      }}
                                      className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800 transition"
                                    >
                                      {copiedToken ? <CheckCircle className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <button
                              type="button"
                              disabled={waDisconnecting}
                              onClick={handleDisconnectWhatsApp}
                              className="flex items-center gap-1.5 px-4 py-2 border border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waDisconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                              Desconectar WhatsApp
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div className="p-3.5 bg-blue-500/5 border border-blue-500/10 rounded-xl space-y-1">
                            <span className="text-xs font-bold text-blue-300 block">¿Cómo conectar la API oficial?</span>
                            <p className="text-[10px] text-gray-400 leading-relaxed">
                              Ingresa el <strong>Phone Number ID</strong>, el <strong>App Secret</strong> y tu <strong>Access Token</strong> permanente de Meta.
                            </p>
                          </div>

                          <div className="space-y-3">
                            <div>
                              <label className="block text-gray-400 font-semibold mb-1 text-[11px]">Phone Number ID (Meta) *</label>
                              <input
                                type="text"
                                placeholder="Ej: 104843928471203"
                                value={waForm.phone_number_id}
                                onChange={e => setWaForm(prev => ({ ...prev, phone_number_id: e.target.value }))}
                                className="w-full bg-[#0c101c] border border-gray-850 focus:border-green-500 rounded-xl px-4 py-2 text-white focus:outline-none text-xs transition-all"
                              />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                              <div>
                                <label className="block text-gray-400 font-semibold mb-1 text-[11px]">App Secret de Meta *</label>
                                <div className="relative">
                                  <input
                                    type={showWaSecrets ? "text" : "password"}
                                    placeholder="Meta App Secret"
                                    value={waForm.app_secret}
                                    onChange={e => setWaForm(prev => ({ ...prev, app_secret: e.target.value }))}
                                    className="w-full bg-[#0c101c] border border-gray-850 focus:border-green-500 rounded-xl pl-4 pr-10 py-2 text-white focus:outline-none text-xs transition-all font-mono"
                                  />
                                  <button
                                    type="button"
                                    onClick={() => setShowWaSecrets(!showWaSecrets)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition"
                                  >
                                    {showWaSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                  </button>
                                </div>
                              </div>

                              <div>
                                <label className="block text-gray-400 font-semibold mb-1 text-[11px]">Verify Token del Webhook *</label>
                                <input
                                  type="text"
                                  placeholder="Ej: genia_verify_token"
                                  value={waForm.verify_token}
                                  onChange={e => setWaForm(prev => ({ ...prev, verify_token: e.target.value }))}
                                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-green-500 rounded-xl px-4 py-2 text-white focus:outline-none text-xs transition-all font-mono"
                                />
                              </div>
                            </div>

                            <div>
                              <label className="block text-gray-400 font-semibold mb-1 text-[11px]">Meta Access Token Permanente *</label>
                              <div className="relative">
                                <textarea
                                  rows={2}
                                  placeholder="EATB..."
                                  value={waForm.access_token}
                                  onChange={e => setWaForm(prev => ({ ...prev, access_token: e.target.value }))}
                                  className="w-full bg-[#0c101c] border border-gray-850 focus:border-green-500 rounded-xl pl-4 pr-10 py-2 text-white focus:outline-none text-xs transition-all font-mono resize-none"
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowWaSecrets(!showWaSecrets)}
                                  className="absolute right-3 top-4 text-gray-500 hover:text-white transition"
                                >
                                  {showWaSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                              </div>
                            </div>
                          </div>

                          <div className="flex justify-end">
                            <button
                              type="button"
                              disabled={waConnecting}
                              onClick={handleConnectWhatsApp}
                              className="flex items-center gap-1.5 px-5 py-2 border border-green-500/25 bg-green-500/10 text-green-400 hover:bg-green-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waConnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Phone className="w-3.5 h-3.5" />}
                              Conectar WhatsApp
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* VISTA 3: Proveedor CÓDIGO QR (WAHA) */}
                  {waStatus?.whatsapp_provider === "waha" && (
                    <div className="space-y-5">
                      {waStatus?.connected ? (
                        <div className="space-y-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-green-500/[0.02] p-4 border border-green-500/10 rounded-xl">
                            <div>
                              <span className="text-gray-400 text-[10px] block">Nombre del Dispositivo Vinculado</span>
                              <span className="text-white text-xs font-semibold">{waStatus.display_name || 'Línea WAHA Conectada'}</span>
                            </div>
                            <div>
                              <span className="text-gray-400 text-[10px] block">Número de Teléfono</span>
                              <span className="text-white text-xs font-semibold">+{waStatus.phone_number || 'No disponible'}</span>
                            </div>
                            <div className="md:col-span-2">
                              <span className="text-gray-400 text-[10px] block">ID de Sesión WAHA</span>
                              <span className="font-mono text-gray-300 text-xs">{waStatus.whatsapp_qr_instance_name}</span>
                            </div>
                          </div>

                          <div className="bg-[#070b16]/60 p-4 border border-gray-850 rounded-xl space-y-2">
                            <span className="text-xs font-bold text-blue-400 block">Webhook de Eventos WAHA</span>
                            <span className="text-gray-400 text-[10px] block mb-1">Ruta del Webhook Activo</span>
                            <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-lg p-2 font-mono">
                              <span className="text-gray-300 truncate flex-1 text-[11px]">
                                {typeof window !== "undefined" ? `${window.location.origin}${waStatus.webhook_url}` : `https://plataforma.genia.com.co${waStatus.webhook_url}`}
                              </span>
                            </div>
                            <p className="text-[10px] text-gray-500">
                              Los mensajes entrantes son recibidos automáticamente desde tu servidor WAHA (WhatsApp HTTP API).
                            </p>
                          </div>

                          <div className="flex justify-end gap-3">
                            <button
                              type="button"
                              disabled={waConnecting}
                              onClick={handleRestartWhatsAppWaha}
                              className="flex items-center gap-1.5 px-4 py-2 border border-blue-500/25 bg-blue-500/10 text-blue-400 hover:bg-blue-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waConnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                              Reiniciar Sesión WAHA
                            </button>
                            <button
                              type="button"
                              disabled={waDisconnecting}
                              onClick={handleDisconnectWhatsAppWaha}
                              className="flex items-center gap-1.5 px-4 py-2 border border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waDisconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                              Desconectar WAHA
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-5">
                          {waStatus?.qr_code ? (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4">
                              <span className="text-xs font-bold text-white">Escanea el Código QR (WAHA)</span>
                              <p className="text-[10px] text-gray-400 text-center max-w-sm leading-relaxed">
                                Abre WhatsApp en tu celular, ve a <strong>Dispositivos Vinculados</strong> y escanea este código para conectar el agente vía WAHA.
                              </p>

                              <div className="p-4 bg-white rounded-xl border border-gray-700 shadow-md">
                                <img
                                  src={waStatus.qr_code}
                                  alt="Código QR WhatsApp WAHA"
                                  className="w-44 h-44 object-contain"
                                />
                              </div>

                              <div className="flex items-center gap-2 text-xs text-green-400 font-medium">
                                <Loader2 className="w-4 h-4 animate-spin text-green-400" />
                                <span>Esperando escaneo en el móvil...</span>
                              </div>

                              <div className="flex flex-wrap justify-center gap-3 pt-2">
                                <button
                                  type="button"
                                  onClick={handleRestartWhatsAppWaha}
                                  className="px-4 py-2 bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700 rounded-xl transition text-xs font-semibold cursor-pointer"
                                >
                                  Regenerar QR
                                </button>
                                <button
                                  type="button"
                                  onClick={handleDisconnectWhatsAppWaha}
                                  className="px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/25 rounded-xl transition text-xs font-semibold cursor-pointer"
                                >
                                  Cancelar
                                </button>
                                {waStatus?.is_mock_mode && (
                                  <button
                                    type="button"
                                    onClick={handleSimulateScanWaha}
                                    className="px-4 py-2 bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/35 rounded-xl transition text-xs font-bold flex items-center gap-1 cursor-pointer animate-bounce"
                                  >
                                    ⚡ Simular Escaneo
                                  </button>
                                )}
                              </div>
                            </div>
                          ) : waQrRequested && !waStatus.qr_code ? (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4 text-center">
                              <div className="flex items-center gap-2 p-3 bg-blue-500/10 rounded-xl">
                                <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                              </div>
                              <span className="text-xs font-bold text-white">Esperando código QR...</span>
                              <p className="text-[10px] text-gray-400 max-w-sm leading-relaxed">
                                La sesión WAHA se está iniciando. El código QR aparecerá automáticamente cuando esté listo.
                              </p>
                              <div className="flex gap-2">
                                <button
                                  type="button"
                                  onClick={() => { fetchWhatsAppStatus(); }}
                                  className="px-4 py-2 bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/25 rounded-xl transition text-xs font-semibold cursor-pointer"
                                >
                                  <RefreshCw className="w-3.5 h-3.5 inline mr-1" />
                                  Verificar conexión
                                </button>
                                <button
                                  type="button"
                                  onClick={handleDisconnectWhatsAppWaha}
                                  className="px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/25 rounded-xl transition text-xs font-semibold cursor-pointer"
                                >
                                  Cancelar
                                </button>
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4 text-center">
                              <span className="text-xs font-bold text-white">Vincular mediante Código QR (WAHA)</span>
                              <p className="text-[10px] text-gray-400 max-w-sm leading-relaxed">
                                WAHA (WhatsApp HTTP API) es una alternativa open-source para vincular cualquier número de WhatsApp sin depender de Meta Developer Portal.
                              </p>

                              <button
                                type="button"
                                disabled={waConnecting}
                                onClick={handleConnectWhatsAppWaha}
                                className="flex items-center gap-2 px-5 py-2.5 bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30 rounded-xl transition text-xs font-bold disabled:opacity-50 cursor-pointer"
                              >
                                {waConnecting ? (
                                  <>
                                    <Loader2 className="w-4 h-4 animate-spin text-green-400" />
                                    <span>Generando sesión...</span>
                                  </>
                                ) : (
                                  <>
                                    <Phone className="w-4 h-4" />
                                    <span>Generar Código QR</span>
                                  </>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* VISTA 2: Proveedor CÓDIGO QR */}
                  {waStatus?.whatsapp_provider === "qr_code" && (
                    <div className="space-y-5">
                      {waStatus?.connected ? (
                        <div className="space-y-4">
                          {/* Detalles del número QR */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-green-500/[0.02] p-4 border border-green-500/10 rounded-xl">
                            <div>
                              <span className="text-gray-400 text-[10px] block">Nombre del Dispositivo Vinculado</span>
                              <span className="text-white text-xs font-semibold">{waStatus.display_name || 'Línea QR Conectada'}</span>
                            </div>
                            <div>
                              <span className="text-gray-400 text-[10px] block">Número de Teléfono</span>
                              <span className="text-white text-xs font-semibold">+{waStatus.phone_number || 'No disponible'}</span>
                            </div>
                            <div className="md:col-span-2">
                              <span className="text-gray-400 text-[10px] block">ID de Instancia</span>
                              <span className="font-mono text-gray-300 text-xs">{waStatus.whatsapp_qr_instance_name}</span>
                            </div>
                          </div>

                          {/* Webhook del QR */}
                          <div className="bg-[#070b16]/60 p-4 border border-gray-850 rounded-xl space-y-2">
                            <span className="text-xs font-bold text-blue-400 block">Webhook de Eventos QR</span>
                            <span className="text-gray-400 text-[10px] block mb-1">Ruta del Webhook Activo</span>
                            <div className="flex items-center gap-2 bg-[#0c101c] border border-gray-800 rounded-lg p-2 font-mono">
                              <span className="text-gray-300 truncate flex-1 text-[11px]">
                                {typeof window !== "undefined" ? `${window.location.origin}${waStatus.webhook_url}` : `https://plataforma.genia.com.co${waStatus.webhook_url}`}
                              </span>
                            </div>
                            <p className="text-[10px] text-gray-500">
                              Los eventos y mensajes entrantes son recibidos automáticamente desde tu middleware de códigos QR.
                            </p>
                          </div>

                          <div className="flex justify-end gap-3">
                            <button
                              type="button"
                              disabled={waConnecting}
                              onClick={handleRestartWhatsAppQR}
                              className="flex items-center gap-1.5 px-4 py-2 border border-blue-500/25 bg-blue-500/10 text-blue-400 hover:bg-blue-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waConnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                              Reiniciar Sesión QR
                            </button>
                            <button
                              type="button"
                              disabled={waDisconnecting}
                              onClick={handleDisconnectWhatsAppQR}
                              className="flex items-center gap-1.5 px-4 py-2 border border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/15 rounded-xl transition text-xs font-semibold disabled:opacity-50 cursor-pointer"
                            >
                              {waDisconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                              Desconectar Línea QR
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-5">
                          {waStatus?.qr_code ? (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4">
                              <span className="text-xs font-bold text-white">Escanea el Código QR</span>
                              <p className="text-[10px] text-gray-400 text-center max-w-sm leading-relaxed">
                                Abre WhatsApp en tu celular, ve a <strong>Dispositivos Vinculados</strong> y escanea este código para conectar el agente de inmediato.
                              </p>
                              
                              {/* QR Code Container */}
                              <div className="p-4 bg-white rounded-xl border border-gray-700 shadow-md">
                                <img
                                  src={waStatus.qr_code}
                                  alt="Código QR WhatsApp"
                                  className="w-44 h-44 object-contain"
                                />
                              </div>

                              <div className="flex items-center gap-2 text-xs text-green-400 font-medium">
                                <Loader2 className="w-4 h-4 animate-spin text-green-400" />
                                <span>Esperando escaneo en el móvil...</span>
                              </div>

                              {/* Botones de Acción QR */}
                              <div className="flex flex-wrap justify-center gap-3 pt-2">
                                  <button
                                    type="button"
                                    onClick={handleRestartWhatsAppQR}
                                    className="px-4 py-2 bg-gray-800 text-gray-300 hover:bg-gray-700 border border-gray-700 rounded-xl transition text-xs font-semibold cursor-pointer"
                                  >
                                    Regenerar QR
                                  </button>
                                <button
                                  type="button"
                                  onClick={handleDisconnectWhatsAppQR}
                                  className="px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/25 rounded-xl transition text-xs font-semibold cursor-pointer"
                                >
                                  Cancelar
                                </button>
                                {waStatus?.is_mock_mode && (
                                  <button
                                    type="button"
                                    onClick={handleSimulateScan}
                                    className="px-4 py-2 bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/35 rounded-xl transition text-xs font-bold flex items-center gap-1 cursor-pointer animate-bounce"
                                  >
                                    ⚡ Simular Escaneo
                                  </button>
                                )}
                              </div>
                            </div>
                          ) : waStatus?.whatsapp_qr_instance_name && !waStatus.qr_code ? (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4 text-center">
                              <div className="flex items-center gap-2 p-3 bg-blue-500/10 rounded-xl">
                                <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                              </div>
                              <span className="text-xs font-bold text-white">Esperando código QR...</span>
                              <p className="text-[10px] text-gray-400 max-w-sm leading-relaxed">
                                La instancia se está iniciando. El código QR aparecerá automáticamente cuando esté listo.
                              </p>
                              <button
                                type="button"
                                onClick={handleDisconnectWhatsAppQR}
                                className="px-4 py-2 bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/25 rounded-xl transition text-xs font-semibold cursor-pointer"
                              >
                                Cancelar
                              </button>
                            </div>
                          ) : (
                            <div className="flex flex-col items-center p-6 bg-[#070b16]/60 border border-gray-850 rounded-xl space-y-4 text-center">
                              <span className="text-xs font-bold text-white">Vincular mediante Código QR</span>
                              <p className="text-[10px] text-gray-400 max-w-sm leading-relaxed">
                                Este método te permite vincular cualquier número de WhatsApp activo sin necesidad de crear una cuenta en Meta Developer Portal.
                              </p>
                              
                              <button
                                type="button"
                                disabled={waConnecting}
                                onClick={handleConnectWhatsAppQR}
                                className="flex items-center gap-2 px-5 py-2.5 bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30 rounded-xl transition text-xs font-bold disabled:opacity-50 cursor-pointer"
                              >
                                {waConnecting ? (
                                  <>
                                    <Loader2 className="w-4 h-4 animate-spin text-green-400" />
                                    <span>Generando instancia...</span>
                                  </>
                                ) : (
                                  <>
                                    <Phone className="w-4 h-4" />
                                    <span>Generar Código QR</span>
                                  </>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Error banner */}
                  {waStatus?.error && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-[10px] leading-relaxed">
                      <span className="font-bold block mb-0.5">⚠️ Error en la conexión activa:</span>
                      {waStatus.error}
                      <span className="block mt-1 text-gray-400">
                        Por favor verifica la configuración y vuelve a intentar la conexión.
                      </span>
                    </div>
                  )}

                </div>
              )}
            </div>
          )}
        </div>

        {/* ── SECCIÓN 6: INTEGRACIÓN DE GOOGLE CALENDAR ── */}
        <div className="glow-card rounded-2xl overflow-hidden">
          <button
            type="button"
            onClick={() => toggleSection("calendar")}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Calendar className="w-4 h-4 text-emerald-400" />
              </div>
              <span className="font-bold text-white text-sm">Google Calendar</span>
              {calStatus?.connected ? (
                <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 text-[10px] rounded-full font-bold">Activo</span>
              ) : (
                <span className="px-2 py-0.5 bg-gray-800 text-gray-400 text-[10px] rounded-full font-bold">Inactivo</span>
              )}
            </div>
            {expandedSections.calendar ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
          </button>

          {expandedSections.calendar && (
            <div className="px-6 pb-6 border-t border-gray-800/50 pt-4 space-y-4">
              <div className="p-4 bg-blue-500/5 border border-blue-500/10 rounded-xl space-y-2">
                <span className="text-xs font-bold text-blue-300 block">¿Cómo obtener tus credenciales de Google Calendar?</span>
                <ol className="list-decimal pl-4 text-[10px] text-gray-400 space-y-1 leading-relaxed">
                  <li>Ve a la <a href="https://console.cloud.google.com/" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">Google Cloud Console</a> y crea o selecciona un proyecto.</li>
                  <li>Habilita la <strong>Google Calendar API</strong> desde la biblioteca de APIs.</li>
                  <li>Ve a <strong>APIs & Services &gt; Credentials</strong> y configura la pantalla de consentimiento OAuth.</li>
                  <li>Crea credenciales de tipo <strong>OAuth Client ID</strong> (Application type: Web application).</li>
                  <li>Añade como URI de redirección autorizado (Authorized redirect URIs): <br/>
                    <code className="bg-[#070b13] px-1.5 py-0.5 rounded font-mono text-[9px] text-gray-300">
                      {typeof window !== "undefined" ? `${window.location.origin}/api/calendar/${id}/callback` : `https://plataforma.genia.com.co/api/calendar/${id}/callback`}
                    </code>
                  </li>
                  <li>Copia el <strong>Client ID</strong> y el <strong>Client Secret</strong> e ingrésalos abajo.</li>
                </ol>
              </div>

              {calStatus?.connected ? (
                <div className="space-y-4 animate-fadeIn">
                  {/* Connected Status Card */}
                  <div className="p-4 bg-emerald-500/[0.02] border border-emerald-500/10 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="text-gray-400 text-[10px] block">Cuenta conectada</span>
                      <span className="text-white text-xs font-bold font-mono">{calStatus.email}</span>
                    </div>
                    <button
                      type="button"
                      disabled={calDisconnecting}
                      onClick={handleDisconnectCalendar}
                      className="px-4 py-2 border border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/15 rounded-xl transition text-xs font-semibold cursor-pointer flex items-center gap-1.5"
                    >
                      {calDisconnecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <X className="w-3.5 h-3.5" />}
                      Desconectar
                    </button>
                  </div>

                  {/* Upcoming events preview */}
                  <div className="space-y-2">
                    <span className="text-gray-300 font-bold text-xs block">Próximos Eventos (7 días)</span>
                    {calEventsLoading ? (
                      <div className="flex justify-center py-6">
                        <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
                      </div>
                    ) : calEvents.length > 0 ? (
                      <div className="max-h-60 overflow-y-auto space-y-2 border border-gray-850 p-2 rounded-xl bg-gray-900/10">
                        {calEvents.map((evt: any) => {
                          const start = new Date(evt.start);
                          return (
                            <div key={evt.id} className="p-2.5 bg-gray-900/30 border border-gray-800 rounded-lg flex items-center justify-between text-[11px]">
                              <div>
                                <span className="text-white font-bold block">{evt.title}</span>
                                <span className="text-gray-400">{start.toLocaleString()}</span>
                              </div>
                              <div className="text-right">
                                {evt.attendees && evt.attendees.length > 0 && (
                                  <span className="text-[10px] text-blue-400 block max-w-40 truncate" title={evt.attendees.join(", ")}>
                                    {evt.attendees[0]}
                                  </span>
                                )}
                                <span className="text-[9px] text-gray-500 block uppercase font-bold">{evt.status}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center py-6 border border-dashed border-gray-800 rounded-xl text-gray-500 text-[11px] italic">
                        No hay eventos programados en los próximos 7 días.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-3 animate-fadeIn">
                  {/* Credentials Fields */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-gray-400 font-semibold mb-1 text-[11px]">Client ID de Google *</label>
                      <input
                        type="text"
                        placeholder="Ingresa tu Google Client ID"
                        value={form.google_calendar_client_id}
                        onChange={e => setForm(prev => ({ ...prev, google_calendar_client_id: e.target.value }))}
                        className="w-full bg-[#0c101c] border border-gray-850 focus:border-emerald-500 rounded-xl px-4 py-2 text-white focus:outline-none text-xs transition-all font-mono"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-400 font-semibold mb-1 text-[11px]">Client Secret de Google *</label>
                      <div className="relative">
                        <input
                          type={showCalSecrets ? "text" : "password"}
                          placeholder={agent.google_calendar_client_id ? "•••••••••••••••• (Cifrado - dejar en blanco para no modificar)" : "Ingresa tu Google Client Secret"}
                          value={form.google_calendar_client_secret}
                          onChange={e => setForm(prev => ({ ...prev, google_calendar_client_secret: e.target.value }))}
                          className="w-full bg-[#0c101c] border border-gray-850 focus:border-emerald-500 rounded-xl pl-4 pr-10 py-2 text-white focus:outline-none text-xs transition-all font-mono"
                        />
                        <button
                          type="button"
                          onClick={() => setShowCalSecrets(!showCalSecrets)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition"
                        >
                          {showCalSecrets ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="button"
                      onClick={handleConnectCalendar}
                      className="flex items-center gap-1.5 px-5 py-2 border border-emerald-500/25 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/15 rounded-xl transition text-xs font-semibold cursor-pointer"
                    >
                      <Calendar className="w-3.5 h-3.5" />
                      Guardar y Conectar Google Calendar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── SECCIÓN 7: ENTRENAMIENTO VISUAL ── */}
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
                    <div className="space-y-4">
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
                            placeholder="Ej. $50.000 COP/hora o Gratis"
                            value={imagePrice}
                            onChange={e => setImagePrice(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Descripción detallada</label>
                          <textarea
                            rows={3}
                            placeholder="Ej. Espacio privado con capacidad para 10 personas, aire acondicionado..."
                            value={imageDescription}
                            onChange={e => setImageDescription(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none resize-none leading-relaxed"
                          />
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleUploadAndGenerateTraining()}
                        disabled={!uploadImageFile || !detectedProduct || !imageDescription || !imagePrice || isUploadingImage}
                        className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                      >
                        <Sparkles className="w-4 h-4 text-yellow-350" />
                        Subir y Entrenar con IA
                      </button>
                    </div>
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
                    <div className="space-y-4">
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
                            value={detectedProduct}
                            onChange={e => setDetectedProduct(e.target.value)}
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Descripción del Agente</label>
                          <textarea
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
                            value={imageKeywords}
                            onChange={e => setImageKeywords(e.target.value)}
                            placeholder="ej: sala juntas, fotos sala, precio sala"
                            className="w-full bg-[#070b13] border border-gray-850 focus:border-blue-500 rounded-xl px-3 py-2 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1">Instrucción para el Prompt</label>
                          <textarea
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
                          type="button"
                          onClick={() => handleConfirmTraining()}
                          className="flex-1 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl font-bold shadow-lg transition cursor-pointer"
                        >
                          Entrenar
                        </button>
                      </div>
                    </div>
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
