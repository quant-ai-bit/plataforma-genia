"use client";

import React, { useState, useEffect, useRef } from "react";
import { use } from "react";
import { getApiBaseUrl } from "../../../../lib/api";
import { Bot, Send, Loader2 } from "lucide-react";

export default function PublicChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [agentName, setAgentName] = useState<string>("");
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [convId, setConvId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const baseUrl = getApiBaseUrl();

  useEffect(() => {
    async function fetchAgent() {
      try {
        const res = await fetch(`${baseUrl}/api/public/agent/${id}`);
        if (res.ok) {
          const data = await res.json();
          setAgentName(data.name);
        } else {
          setAgentName("Agente");
        }
      } catch {
        setAgentName("Agente");
      } finally {
        setLoading(false);
      }
    }
    fetchAgent();
  }, [id, baseUrl]);

  useEffect(() => {
    if (!loading && messages.length === 0) {
      setMessages([
        {
          role: "assistant",
          content: agentName
            ? `Hola! Soy ${agentName}. Escribe lo que necesites y te atenderé.`
            : "Hola! Escribe lo que necesites y te atenderé.",
        },
      ]);
    }
  }, [loading, agentName, messages.length]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    const text = input;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const res = await fetch(`${baseUrl}/api/public/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_id: id,
          message: text,
          conversation_id: convId,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setConvId(data.conversation_id);
        setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      } else {
        const errData = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${errData.detail || "Error del servidor"}` },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error de conexión con el servidor." },
      ]);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full p-4 md:p-6">
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#0c101c]/60 border border-[#1e293b] rounded-2xl">
          <Bot className="w-5 h-5 text-blue-400" />
          <span className="text-sm font-bold text-white">{agentName || "Agente Genia"}</span>
        </div>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 bg-red-950/20 border border-red-500/30 rounded-xl text-xs text-red-300 text-center">
          {error}
        </div>
      )}

      <div className="flex-1 bg-[#0c101c]/50 border border-gray-800 rounded-2xl overflow-hidden flex flex-col min-h-0">
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 min-h-0">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-md leading-relaxed ${
                  msg.role === "user"
                    ? "bg-gradient-to-tr from-blue-600 to-indigo-600 text-white rounded-br-none"
                    : "bg-gray-800 text-gray-100 rounded-bl-none border border-gray-700/60"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-gray-800 text-gray-400 rounded-2xl rounded-bl-none px-4 py-3 text-sm flex gap-1 border border-gray-700/60">
                <span className="animate-bounce font-extrabold text-blue-400">.</span>
                <span className="animate-bounce delay-100 font-extrabold text-indigo-400">.</span>
                <span className="animate-bounce delay-200 font-extrabold text-purple-400">.</span>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleSend} className="p-4 bg-[#0d1321]/80 border-t border-gray-850 flex gap-3 items-center flex-shrink-0">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={agentName ? `Escribe un mensaje para ${agentName}...` : "Escribe un mensaje..."}
            className="flex-1 bg-[#070b13] border border-gray-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="p-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 disabled:opacity-50 text-white rounded-xl shadow-lg transition duration-200 flex items-center justify-center cursor-pointer"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
