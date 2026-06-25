"use client";

import React, { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../../../lib/AppContext";
import { authenticatedFetch } from "../../../../../lib/api";
import {
  ArrowLeft,
  Bot,
  RefreshCw,
  Send,
  UserCheck,
  CheckCircle,
  Loader2,
  Mic,
  Square
} from "lucide-react";

export default function AgentChatSandbox({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const {
    agents,
    isBackendOnline,
    loadBackendData,
    loadAgentUsage
  } = useAppContext();

  const [agent, setAgent] = useState<any>(null);
  
  // Chat States
  const [chatConvId, setChatConvId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState<string>("");
  const [isChatSending, setIsChatSending] = useState<boolean>(false);
  const [liveCapturedLead, setLiveCapturedLead] = useState<any>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Audio Recording States
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

  useEffect(() => {
    const foundAgent = agents.find(a => a.id === id);
    if (foundAgent) {
      setAgent(foundAgent);
    }
  }, [id, agents]);

  const startNewChatSession = () => {
    setChatConvId(null);
    setChatMessages([]);
    setLiveCapturedLead(null);
    
    const activeAgentName = agent?.name || "Agente Genia";
    setChatMessages([
      {
        role: "assistant",
        content: `¡Hola! Soy el simulador de ${activeAgentName}. Escribe un mensaje aquí para comenzar a probar mi comportamiento.`
      }
    ]);
  };

  useEffect(() => {
    if (agent && chatMessages.length === 0) {
      startNewChatSession();
    }
  }, [agent, chatMessages.length]);

  useEffect(() => {
    // Limpiar el chat cuando cambie el agente (ID)
    setChatConvId(null);
    setChatMessages([]);
    setLiveCapturedLead(null);
  }, [id]);


  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, isChatSending]);

  useEffect(() => {
    return () => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    };
  }, [mediaRecorder]);

  const startRecording = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Tu navegador no soporta la grabación de audio o requiere HTTPS.");
        return;
      }
      
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: "audio/webm" });
        await handleSendAudio(audioBlob);
        
        // Detener todos los tracks para apagar el micrófono
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
    } catch (err) {
      console.error("Error al acceder al micrófono:", err);
      alert("No se pudo acceder al micrófono. Por favor verifica los permisos.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleSendAudio = async (audioBlob: Blob) => {
    setIsChatSending(true);
    // Añadimos mensaje temporal en la interfaz
    setChatMessages(prev => [...prev, { role: "user", content: "🎤 [Nota de voz enviada. Procesando...]" }]);

    try {
      const formData = new FormData();
      formData.append("file", audioBlob, "recording.webm");

      const resTranscribe = await authenticatedFetch("/api/chat/transcribe", {
        method: "POST",
        body: formData
      });

      if (!resTranscribe.ok) {
        throw new Error("Error en la transcripción de audio.");
      }

      const dataTranscribe = await resTranscribe.json();
      const transcribedText = dataTranscribe.text;

      if (!transcribedText || !transcribedText.trim()) {
        setChatMessages(prev => [
          ...prev.slice(0, -1),
          { role: "assistant", content: "No se pudo entender la nota de voz. Intenta hablar de nuevo." }
        ]);
        setIsChatSending(false);
        return;
      }

      // Reemplazamos el mensaje temporal con el texto transcrito real
      setChatMessages(prev => [
        ...prev.slice(0, -1),
        { role: "user", content: `🎤 (Nota de voz): "${transcribedText}"` }
      ]);

      // Enviar el texto al agente
      const chatPayload = {
        agent_id: id,
        message: transcribedText,
        conversation_id: chatConvId
      };

      const res = await authenticatedFetch(`/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chatPayload)
      });

      if (res.ok) {
        const data = await res.json();
        setChatConvId(data.conversation_id);
        setChatMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
        
        loadBackendData();
        loadAgentUsage(id);

        setTimeout(async () => {
          const resLeads = await authenticatedFetch(`/api/leads/`);
          if (resLeads.ok) {
            const currentLeads = await resLeads.json();
            const matchingLead = currentLeads.find((l: any) => l.conversation_id === data.conversation_id);
            if (matchingLead) {
              setLiveCapturedLead(matchingLead);
            }
          }
        }, 1000);
      } else {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: "assistant", content: `Error: ${JSON.stringify(data.detail)}` }]);
      }
    } catch (err) {
      console.error("Error procesando nota de voz:", err);
      setChatMessages(prev => [
        ...prev.slice(0, -1),
        { role: "assistant", content: "Lo siento, tuve un problema al procesar tu nota de voz." }
      ]);
    } finally {
      setIsChatSending(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatSending) return;

    const userMessageText = chatInput;
    setChatMessages(prev => [...prev, { role: "user", content: userMessageText }]);
    setChatInput("");
    setIsChatSending(true);

    if (!isBackendOnline) {
      // Local Simulation Mode
      setTimeout(() => {
        let reply = "Esta es una respuesta simulada ya que el backend no está conectado. Para capturar tus datos, por favor inicia el backend de la PLATAFORMA GENIA.";
        
        // Match name/email/phone fields locally to simulate capture
        if (
          userMessageText.toLowerCase().includes("correo") || 
          userMessageText.toLowerCase().includes("email") || 
          userMessageText.toLowerCase().includes("@")
        ) {
          setLiveCapturedLead({
            name: "Usuario de prueba",
            email: "ejemplo@servidor.com",
            business_type: "Tecnología",
            num_employees: 10
          });
          reply = "¡Excelente! Acabo de detectar tus datos de contacto y negocio. He guardado a 'Usuario de prueba' en la sección de leads.";
        }

        setChatMessages(prev => [...prev, { role: "assistant", content: reply }]);
        setIsChatSending(false);
      }, 1000);
      return;
    }

    try {
      const chatPayload = {
        agent_id: id,
        message: userMessageText,
        conversation_id: chatConvId
      };

      const res = await authenticatedFetch(`/api/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chatPayload)
      });

      if (res.ok) {
        const data = await res.json();
        setChatConvId(data.conversation_id);
        setChatMessages(prev => [...prev, { role: "assistant", content: data.reply }]);
        
        // Refresh usage metrics in context
        loadBackendData();
        loadAgentUsage(id);

        // Fetch captured leads after message to check if a lead was parsed
        setTimeout(async () => {
          const resLeads = await authenticatedFetch(`/api/leads/`);
          if (resLeads.ok) {
            const currentLeads = await resLeads.json();
            const matchingLead = currentLeads.find((l: any) => l.conversation_id === data.conversation_id);
            if (matchingLead) {
              setLiveCapturedLead(matchingLead);
            }
          }
        }, 1000);

      } else {
        const data = await res.json();
        setChatMessages(prev => [...prev, { role: "assistant", content: `Error: ${JSON.stringify(data.detail)}` }]);
      }
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: "assistant", content: "Error de comunicación con el backend." }]);
    } finally {
      setIsChatSending(false);
    }
  };

  // Helper to parse markdown images in chat bubbles
  const renderMessageContent = (content: string) => {
    const imageRegex = /!\[(.*?)\]\((.*?)\)/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    while ((match = imageRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={lastIndex}>{content.substring(lastIndex, match.index)}</span>);
      }
      const alt = match[1];
      const url = match[2];
      parts.push(
        <div key={match.index} className="my-2 p-1.5 bg-[#0d1321]/50 border border-gray-850 rounded-xl max-w-sm overflow-hidden animate-fadeIn">
          <img src={url} alt={alt} className="rounded-lg max-h-48 object-cover w-full" />
          <span className="text-[10px] text-gray-500 mt-1 block text-center italic">{alt}</span>
        </div>
      );
      lastIndex = imageRegex.lastIndex;
    }
    if (lastIndex < content.length) {
      parts.push(<span key={lastIndex}>{content.substring(lastIndex)}</span>);
    }
    return parts.length > 0 ? parts : content;
  };

  if (!agent) {
    return (
      <div className="flex h-64 items-center justify-center text-white">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-gray-400 text-xs">Cargando simulador...</p>
        </div>
      </div>
    );
  }

  // Fields to display on the Live Parser
  const getFieldsToDisplay = () => {
    const fields = [];
    fields.push({
      key: "name",
      label: "Nombre completo",
      required: true,
      value: liveCapturedLead?.name || null
    });

    const emailField = agent.custom_fields?.find((f: any) => f.key === "email");
    const phoneField = agent.custom_fields?.find((f: any) => f.key === "phone");

    fields.push({
      key: "email",
      label: emailField?.label || "Correo electrónico",
      required: emailField?.required || false,
      value: liveCapturedLead?.email || null
    });

    fields.push({
      key: "phone",
      label: phoneField?.label || "Teléfono",
      required: phoneField?.required || false,
      value: liveCapturedLead?.phone || null
    });

    if (agent.custom_fields) {
      agent.custom_fields.forEach((field: any) => {
        if (field.key !== "email" && field.key !== "phone" && field.key !== "name") {
          fields.push({
            key: field.key,
            label: field.label || field.key,
            required: field.required || false,
            value: liveCapturedLead?.custom_data?.[field.key] || null
          });
        }
      });
    }
    return fields;
  };

  const fieldsToDisplay = getFieldsToDisplay();

  return (
    <div className="space-y-6 animate-fadeIn h-[calc(100vh-140px)] flex flex-col text-xs">
      
      {/* Header controls */}
      <div className="flex justify-between items-center bg-gray-900/10 border border-gray-850 p-4 rounded-2xl flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/agents")}
            className="p-2 bg-gray-800 hover:bg-gray-750 text-gray-400 hover:text-white rounded-xl transition cursor-pointer"
            title="Volver"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h3 className="text-sm font-bold text-white">Sandbox: {agent.name}</h3>
            <p className="text-[10px] text-gray-500">Prueba el comportamiento de tu agente de IA en tiempo real.</p>
          </div>
        </div>

        <button
          onClick={startNewChatSession}
          className="flex items-center gap-1.5 py-2 px-3 bg-red-950/20 hover:bg-red-900/30 text-red-400 text-[10px] rounded-xl font-bold border border-red-500/20 transition cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Reiniciar Sesión
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0 overflow-hidden">
        
        {/* Chat window (3 cols) */}
        <div className="lg:col-span-3 flex flex-col bg-[#0c101c]/50 border border-gray-800 rounded-2xl overflow-hidden min-h-0">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 min-h-0">
            {chatMessages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm shadow-md leading-relaxed ${
                    msg.role === "user"
                      ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white rounded-br-none"
                      : "bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700/60"
                  }`}
                >
                  <p>{renderMessageContent(msg.content)}</p>
                </div>
              </div>
            ))}
            
            {isChatSending && (
              <div className="flex justify-start">
                <div className="bg-gray-800 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex gap-1 border border-gray-700/60">
                  <span className="animate-bounce font-extrabold text-blue-400 text-lg">.</span>
                  <span className="animate-bounce delay-100 font-extrabold text-indigo-400 text-lg">.</span>
                  <span className="animate-bounce delay-200 font-extrabold text-purple-400 text-lg">.</span>
                </div>
              </div>
            )}
            
            <div ref={chatEndRef} />
          </div>

          {/* Form input */}
          <form onSubmit={handleSendMessage} className="p-4 bg-[#0d1321]/80 border-t border-gray-850 flex gap-3 items-center flex-shrink-0">
            <input
              type="text"
              value={chatInput}
              disabled={isRecording}
              onChange={e => setChatInput(e.target.value)}
              placeholder={isRecording ? "Grabando audio... Habla ahora. Haz clic en el micrófono rojo para detener y enviar." : `Chatea con ${agent.name}...`}
              className="flex-1 bg-[#070b13] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition disabled:opacity-75"
            />
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isChatSending}
              className={`p-3 rounded-xl shadow-lg transition duration-200 flex items-center justify-center cursor-pointer ${
                isRecording 
                  ? "bg-red-600 hover:bg-red-500 text-white animate-pulse" 
                  : "bg-gray-800 hover:bg-gray-700 text-gray-300"
              }`}
              title={isRecording ? "Detener grabación y enviar" : "Grabar nota de voz"}
            >
              {isRecording ? <Square className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
            <button
              type="submit"
              disabled={isChatSending || !chatInput.trim() || isRecording}
              className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl shadow-lg transition duration-200 flex items-center justify-center cursor-pointer"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Live Parser CRM Side panel (1 col) */}
        <div className="flex flex-col gap-6 overflow-y-auto">
          
          <div className="glow-card-purple p-5 rounded-2xl flex-1 flex flex-col bg-[#0f0a1c]/40 border border-purple-500/10">
            <div className="flex items-center gap-2 border-b border-purple-500/20 pb-4 mb-4">
              <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg border border-purple-500/20 animate-pulse">
                <UserCheck className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white">Parser en Vivo</h4>
                <span className="text-[9px] text-purple-300 font-bold uppercase tracking-wider block">
                  Captura Automática AI
                </span>
              </div>
            </div>

            <div className="space-y-4 flex-1 flex flex-col justify-between">
              <div className="space-y-4">
                {/* Status indicator */}
                {liveCapturedLead ? (
                  <div className="px-3 py-2 bg-green-950/20 border border-green-500/30 rounded-xl text-[10px] flex items-center gap-2 text-green-300">
                    <CheckCircle className="w-3.5 h-3.5 flex-shrink-0 animate-pulse" />
                    <span>¡Datos capturados en vivo!</span>
                  </div>
                ) : (
                  <div className="px-3 py-2 bg-purple-950/20 border border-purple-500/30 rounded-xl text-[10px] flex items-center gap-2 text-purple-300">
                    <Loader2 className="w-3.5 h-3.5 flex-shrink-0 animate-spin" />
                    <span>Escuchando conversación...</span>
                  </div>
                )}

                {/* Captured fields */}
                <div className="space-y-3">
                  {fieldsToDisplay.map((field) => {
                    const isCaptured = field.value !== null && field.value !== undefined && field.value !== "";
                    return (
                      <div 
                        key={field.key} 
                        className={`p-3 rounded-xl border transition-all duration-300 ${
                          isCaptured 
                            ? "bg-green-500/5 border-green-500/25 shadow-[0_0_15px_rgba(34,197,94,0.04)] animate-fadeIn" 
                            : "bg-gray-950/40 border-gray-850"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-gray-400 font-bold text-[10px] flex items-center gap-0.5">
                            {field.label}
                            {field.required && (
                              <span className="text-red-400 text-[9px]">*</span>
                            )}
                          </span>
                          <span className={`text-[7px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            isCaptured 
                              ? "bg-green-500/10 text-green-400 border border-green-500/20" 
                              : "bg-gray-800/50 text-gray-500 border border-gray-800"
                          }`}>
                            {isCaptured ? "Capturado" : "Pendiente"}
                          </span>
                        </div>
                        
                        <div className="mt-1.5 flex items-center justify-between">
                          {isCaptured ? (
                            <span className="text-white font-bold text-xs truncate max-w-[120px]" title={String(field.value)}>
                              {typeof field.value === "object" ? JSON.stringify(field.value) : String(field.value)}
                            </span>
                          ) : (
                            <span className="text-gray-600 italic text-xs">
                              Esperando dato...
                            </span>
                          )}
                          
                          {isCaptured && (
                            <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="text-[9px] text-gray-500 border-t border-gray-850 pt-3 mt-4 leading-relaxed">
                {liveCapturedLead 
                  ? "El lead se ha guardado permanentemente en la base de datos SQL de la plataforma." 
                  : "Los datos se irán mostrando aquí a medida que el agente los identifique y extraiga."}
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
