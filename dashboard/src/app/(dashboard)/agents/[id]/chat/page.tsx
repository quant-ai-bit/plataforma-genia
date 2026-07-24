"use client";

import React, { useState, useEffect, useRef, use } from "react";
import { useRouter } from "next/navigation";
import { useAppContext } from "../../../../../lib/AppContext";
import { authenticatedFetch } from "../../../../../lib/api";
import {
  ArrowLeft,
  RefreshCw,
  Send,
  Share2,
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
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Share
  const [showSharePanel, setShowSharePanel] = useState(false);
  const [copied, setCopied] = useState(false);

  const shareUrl = typeof window !== "undefined" ? `${window.location.origin}/chat/${id}` : "";

  const handleCopyLink = () => {
    navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }).catch(() => {
      prompt("Copia este enlace para compartir tu agente:", shareUrl);
    });
  };

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
        // Detener todos los tracks de inmediato para liberar el micrófono
        stream.getTracks().forEach(track => track.stop());

        const audioBlob = new Blob(chunks, { type: "audio/webm" });
        await handleSendAudio(audioBlob);
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

      const resTranscribe = await authenticatedFetch(`/api/chat/transcribe?agent_id=${id}`, {
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

      const res = await authenticatedFetch(`/api/chat`, {
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
      setTimeout(() => {
        setChatMessages(prev => [...prev, { role: "assistant", content: "Esta es una respuesta simulada ya que el backend no está conectado." }]);
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

      const res = await authenticatedFetch(`/api/chat`, {
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

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSharePanel(!showSharePanel)}
            className={`flex items-center gap-1.5 py-2 px-3 text-[10px] rounded-xl font-bold border transition cursor-pointer ${
              showSharePanel
                ? "bg-blue-950/40 text-blue-300 border-blue-500/40"
                : "bg-blue-950/20 hover:bg-blue-900/30 text-blue-400 border-blue-500/20"
            }`}
          >
            <Share2 className="w-3.5 h-3.5" />
            Compartir
          </button>
          <button
            onClick={startNewChatSession}
            className="flex items-center gap-1.5 py-2 px-3 bg-red-950/20 hover:bg-red-900/30 text-red-400 text-[10px] rounded-xl font-bold border border-red-500/20 transition cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Reiniciar Sesión
          </button>
        </div>
      </div>

      {showSharePanel && (
        <div className="bg-[#0c101c]/80 border border-blue-500/20 rounded-2xl p-4 flex flex-col gap-3 animate-fadeIn flex-shrink-0">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-gray-400 font-semibold uppercase tracking-wider">
              Enlace público para compartir
            </span>
            <button
              onClick={() => setShowSharePanel(false)}
              className="text-[10px] text-gray-500 hover:text-gray-300 transition cursor-pointer"
            >
              Cerrar
            </button>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={shareUrl}
              readOnly
              onClick={(e) => e.currentTarget.select()}
              className="flex-1 bg-[#070b13] border border-gray-700 rounded-xl px-3 py-2 text-xs text-blue-300 font-mono focus:outline-none focus:border-blue-500 transition cursor-text"
            />
            <button
              onClick={handleCopyLink}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs rounded-xl font-bold border transition cursor-pointer flex-shrink-0 ${
                copied
                  ? "bg-green-950/20 text-green-400 border-green-500/20"
                  : "bg-blue-600 hover:bg-blue-500 text-white border-blue-500 shadow-sm"
              }`}
            >
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
          <p className="text-[9px] text-gray-500">
            Cualquier persona con este enlace puede chatear con {agent?.name || "el agente"} sin iniciar sesión.
          </p>
        </div>
      )}

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        
        {/* Chat window */}
        <div className="flex flex-col bg-[#0c101c]/50 border border-gray-800 rounded-2xl overflow-hidden min-h-0">
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

      </div>
    </div>
  );
}
