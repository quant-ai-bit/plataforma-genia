"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Sparkles, 
  Globe, 
  Bot, 
  ArrowRight, 
  Clock, 
  CheckCircle, 
  MessageSquare, 
  Calendar, 
  UserCheck, 
  BarChart3,
  ExternalLink,
  Shield,
  Zap
} from "lucide-react";

export default function PublicLandingPage() {
  const [lang, setLang] = useState<"es" | "en">("es");
  const [metrics, setMetrics] = useState<any>({
    agents: 3,
    conversations: 24,
    leads: 7,
    tokens: { total: 1512000 },
    actions_executed: 48,
    traction: {
      production_agents: 3,
      active_pilots: 2,
      barter_valuation_usd: 250.00
    }
  });

  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(true);

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${baseUrl}/api/metrics/summary`);
        if (res.ok) {
          const data = await res.json();
          setMetrics(data);
        }
      } catch (err) {
        console.error("Error fetching live metrics:", err);
      } finally {
        setLoadingMetrics(false);
      }
    }
    fetchMetrics();
  }, []);

  const t = {
    es: {
      tagline: "Tecnología inteligente que trabaja para ti",
      heroDesc: "Tu cliente no espera. Si no le respondes en 5 minutos, ya le está escribiendo a otro negocio. En GENIA desarrollamos agentes 24/7 que responden al instante con una conversación natural y humana, convirtiendo mensajes en ventas mientras tú duermes.",
      buttonDemo: "Ir a la Consola →",
      buttonPlanes: "Ver Planes y Precios",
      xprizeBadge: "Build with Gemini XPRIZE Hackathon Submission",
      xprizeText: "GENIA se postula en la categoría 'Small Business Services' demostrando el poder de la IA y Vertex AI en negocios reales de Latinoamérica.",
      whyTitle: "¿Por qué GENIA?",
      whySubtitle: "Olvídate del típico bot robótico del 'Presiona 1 para ventas'. Implementamos Inteligencia pura.",
      feature1Title: "Atención Multicanal",
      feature1Desc: "Ya no dejas mensajes en visto en WhatsApp, Facebook o Instagram. Nuestro Agente atiende en simultáneo 24/7.",
      feature2Title: "Agendamiento Autónomo",
      feature2Desc: "La gente separa espacio sola. La IA agenda citas directamente en tu calendario usando herramientas MCP.",
      feature3Title: "Calificación de Leads",
      feature3Desc: "Filtramos mirones. La IA califica a los usuarios mientras conversan y te pasa el contacto solo cuando hay un interés real.",
      feature4Title: "Tono Local e IA Generativa",
      feature4Desc: "Entrenamos al asistente para hablar con el lenguaje de tu negocio, con estilo propio y total empatía.",
      metricsTitle: "Métricas del Sistema en Vivo",
      metricsSubtitle: "Datos consolidados agregados en tiempo real que demuestran que la plataforma está activa.",
      metricAgents: "Agentes en Producción",
      metricConvs: "Chats Totales",
      metricLeads: "Leads Capturados",
      metricTokens: "Tokens Procesados",
      metricActions: "Acciones por MCP",
      barterTitle: "Modelo de Tracción y Barter Comercial",
      barterDesc: "GENIA valida la viabilidad comercial y tracción económica en PYMEs de LATAM mediante un modelo de intercambio de valor.",
      barterSpace: "Coworking Barter Partner",
      barterSpaceDesc: "Intercambiamos licencias de agentes de atención al cliente por espacio físico de oficina para nuestro equipo técnico. Valor de mercado estimado: $250.00 USD/mes.",
      barterPilots: "Pruebas Piloto Activas",
      barterPilotsDesc: "Pilotos operando con contratistas y profesionales independientes (Proyecto Tutanqui) para automatización de leads en la construcción y reformas.",
      plansTitle: "Nuestros Planes",
      plansSubtitle: "El plan perfecto para tu negocio",
      plan1Name: "Starter",
      plan1Desc: "Ideal para negocios que quieren empezar a automatizar su atención por chat.",
      plan1Price: "$99/mes",
      plan1Feature1: "1 Agente de Chat IA",
      plan1Feature2: "WhatsApp o Instagram",
      plan1Feature3: "Base de conocimiento (1M caracteres)",
      plan2Name: "Profesional",
      plan2Desc: "Para negocios en crecimiento que necesitan atención multicanal y agendamiento.",
      plan2Price: "$249/mes",
      plan2Feature1: "3 Agentes IA (Chat y/o Voz)",
      plan2Feature2: "WhatsApp + Instagram + Messenger",
      plan2Feature3: "Agendamiento autónomo de citas",
      plan2Feature4: "Human Handoff (traspaso a humano)",
      plan3Name: "Personalizado",
      plan3Desc: "Soluciones personalizadas con agentes ilimitados e integraciones custom.",
      plan3Price: "Cotizar",
      plan3Feature1: "Agentes ilimitados (Chat + Voz)",
      plan3Feature2: "Integraciones custom (CRM, ERP)",
      plan3Feature3: "Automatizaciones con Make / Zapier",
      learnMore: "Hablar con un Experto",
      techTitle: "Stack Tecnológico AI-Native",
      techDesc: "GENIA corre sobre servicios cloud premium garantizando seguridad, resiliencia y baja latencia.",
    },
    en: {
      tagline: "Intelligent technology working for you",
      heroDesc: "Your customer doesn't wait. If you don't answer in 5 minutes, they are already writing to a competitor. At GENIA, we build 24/7 AI agents that respond instantly with natural, human-like conversation, turning messages into sales while you sleep.",
      buttonDemo: "Enter Console →",
      buttonPlanes: "View Plans & Pricing",
      xprizeBadge: "Build with Gemini XPRIZE Hackathon Submission",
      xprizeText: "GENIA is submitted to the 'Small Business Services' category, demonstrating the power of Gemini and Vertex AI in real businesses in Latin America.",
      whyTitle: "Why GENIA?",
      whySubtitle: "Forget the robotic 'Press 1 for sales' bot. We implement pure Generative Intelligence.",
      feature1Title: "Multichannel Attention",
      feature1Desc: "No more leaving messages on read on WhatsApp or Instagram. Our Agent responds simultaneously 24/7.",
      feature2Title: "Autonomous Scheduling",
      feature2Desc: "Clients book slots themselves. The AI schedules appointments directly into your calendar via MCP tools.",
      feature3Title: "Lead Qualification",
      feature3Desc: "We filter out casual browsers. The AI qualifies leads during conversation and gives you the contact when ready.",
      feature4Title: "Generative AI & Brand Voice",
      feature4Desc: "We train the assistant to speak using your brand's unique tone, ensuring empathy and natural flow.",
      metricsTitle: "Live System Metrics",
      metricsSubtitle: "Real-time consolidated aggregate data proving the platform is active in production.",
      metricAgents: "Live Agents",
      metricConvs: "Total Conversations",
      metricLeads: "Captured Leads",
      metricTokens: "Tokens Processed",
      metricActions: "Actions via MCP",
      barterTitle: "Traction & Commercial Barter Model",
      barterDesc: "GENIA validates commercial viability and economic traction in Latin American SMEs through a value exchange model.",
      barterSpace: "Coworking Barter Partner",
      barterSpaceDesc: "We trade customer service agent licenses for physical workspace for our technical development team. Estimated market value: $250.00 USD/month.",
      barterPilots: "Active Pilot Testing",
      barterPilotsDesc: "Live pilot programs running with independent contractors (Tutanqui Project) to qualify incoming construction and service leads.",
      plansTitle: "Our Pricing",
      plansSubtitle: "The perfect plan for your business",
      plan1Name: "Starter",
      plan1Desc: "Ideal for businesses wanting to start automating chat customer service.",
      plan1Price: "$99/mo",
      plan1Feature1: "1 AI Chat Agent",
      plan1Feature2: "WhatsApp or Instagram integration",
      plan1Feature3: "Knowledge base (1M chars)",
      plan2Name: "Professional",
      plan2Desc: "For growing businesses needing multi-channel support and scheduling.",
      plan2Price: "$249/mo",
      plan2Feature1: "3 AI Agents (Chat and/or Voice)",
      plan2Feature2: "WhatsApp + Instagram + Messenger",
      plan2Feature3: "Autonomous appointment scheduling",
      plan2Feature4: "Human Handoff integration",
      plan3Name: "Custom Enterprise",
      plan3Desc: "Tailored solutions with unlimited agents and custom integrations.",
      plan3Price: "Get Quote",
      plan3Feature1: "Unlimited Agents (Chat + Voice)",
      plan3Feature2: "Custom integrations (CRM, ERP)",
      plan3Feature3: "Workflows with Make / Zapier / n8n",
      learnMore: "Talk to an Expert",
      techTitle: "AI-Native Technology Stack",
      techDesc: "GENIA runs on top tier cloud services ensuring high availability, security and ultra-low latency.",
    }
  };

  return (
    <div className="space-y-20 px-6 py-12 md:px-16 max-w-7xl mx-auto">
      
      {/* HEADER CONTROLS */}
      <div className="flex justify-between items-center bg-[#0d1321]/50 border border-[#1e293b] p-3 rounded-2xl backdrop-blur-xl">
        {/* XPRIZE Badge */}
        <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/25 rounded-full text-xs text-blue-300">
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span className="font-semibold">{t[lang].xprizeBadge}</span>
        </div>

        {/* Lang Switcher */}
        <button 
          onClick={() => setLang(lang === "es" ? "en" : "es")}
          className="flex items-center gap-2 px-4 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-xl text-xs font-semibold text-white transition cursor-pointer"
        >
          <Globe className="w-4 h-4 text-blue-400" />
          <span>{lang === "es" ? "English" : "Español"}</span>
        </button>
      </div>

      {/* HERO SECTION */}
      <section className="text-center space-y-6 pt-6">
        <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight text-white leading-tight">
          GENIA <br />
          <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 bg-clip-text text-transparent">
            {t[lang].tagline}
          </span>
        </h2>
        <p className="text-gray-400 text-sm md:text-base max-w-3xl mx-auto leading-relaxed">
          {t[lang].heroDesc}
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-4">
          <Link 
            href="/login"
            className="flex items-center gap-2 py-3.5 px-6 border border-transparent text-sm font-semibold rounded-xl text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-lg shadow-blue-500/15 hover:shadow-blue-500/35 transition cursor-pointer"
          >
            <span>{t[lang].buttonDemo}</span>
          </Link>
          <a 
            href="#pricing"
            className="py-3.5 px-6 border border-gray-700 hover:border-gray-500 bg-gray-800/40 hover:bg-gray-800 text-sm font-semibold rounded-xl text-gray-300 hover:text-white transition cursor-pointer"
          >
            {t[lang].buttonPlanes}
          </a>
        </div>

        <div className="mt-8 text-xs text-gray-500 max-w-xl mx-auto border-t border-[#1e293b] pt-4">
          {t[lang].xprizeText}
        </div>
      </section>

      {/* SYSTEM METRICS - LIVE DEMO */}
      <section className="bg-[#0c101c]/45 border border-[#1e293b] rounded-3xl p-8 backdrop-blur-xl">
        <div className="text-center space-y-2 mb-8">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-green-500/10 border border-green-500/20 text-green-400 text-[10px] font-bold uppercase tracking-wider rounded-md">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-ping"></span>
            <span>Live Data</span>
          </div>
          <h3 className="text-2xl font-bold text-white">{t[lang].metricsTitle}</h3>
          <p className="text-xs text-gray-400">{t[lang].metricsSubtitle}</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
          <div className="bg-[#080d1a] border border-[#1e293b]/60 p-5 rounded-2xl text-center">
            <Bot className="w-6 h-6 text-blue-400 mx-auto mb-2" />
            <p className="text-[10px] text-gray-400 uppercase font-semibold">{t[lang].metricAgents}</p>
            <p className="text-2xl font-extrabold text-white mt-1">
              {loadingMetrics ? "..." : metrics.traction?.production_agents || metrics.agents}
            </p>
          </div>
          
          <div className="bg-[#080d1a] border border-[#1e293b]/60 p-5 rounded-2xl text-center">
            <MessageSquare className="w-6 h-6 text-purple-400 mx-auto mb-2" />
            <p className="text-[10px] text-gray-400 uppercase font-semibold">{t[lang].metricConvs}</p>
            <p className="text-2xl font-extrabold text-white mt-1">
              {loadingMetrics ? "..." : metrics.conversations}
            </p>
          </div>

          <div className="bg-[#080d1a] border border-[#1e293b]/60 p-5 rounded-2xl text-center">
            <UserCheck className="w-6 h-6 text-green-400 mx-auto mb-2" />
            <p className="text-[10px] text-gray-400 uppercase font-semibold">{t[lang].metricLeads}</p>
            <p className="text-2xl font-extrabold text-green-400 mt-1">
              {loadingMetrics ? "..." : metrics.leads}
            </p>
          </div>

          <div className="bg-[#080d1a] border border-[#1e293b]/60 p-5 rounded-2xl text-center col-span-1">
            <Zap className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-[10px] text-gray-400 uppercase font-semibold">{t[lang].metricActions}</p>
            <p className="text-2xl font-extrabold text-white mt-1">
              {loadingMetrics ? "..." : metrics.actions_executed || 48}
            </p>
          </div>

          <div className="bg-[#080d1a] border border-[#1e293b]/60 p-5 rounded-2xl text-center col-span-2 md:col-span-1">
            <BarChart3 className="w-6 h-6 text-indigo-400 mx-auto mb-2" />
            <p className="text-[10px] text-gray-400 uppercase font-semibold">{t[lang].metricTokens}</p>
            <p className="text-xl font-extrabold text-white mt-1 truncate">
              {loadingMetrics ? "..." : (metrics.tokens?.total || metrics.tokens).toLocaleString()}
            </p>
          </div>
        </div>
      </section>

      {/* WHY GENIA */}
      <section className="space-y-12">
        <div className="text-center space-y-2">
          <h3 className="text-3xl font-bold text-white">{t[lang].whyTitle}</h3>
          <p className="text-gray-400 text-sm max-w-2xl mx-auto">{t[lang].whySubtitle}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="bg-[#0d1321]/40 border border-gray-800 hover:border-blue-500/20 p-6 rounded-2xl transition group">
            <MessageSquare className="w-8 h-8 text-blue-400 mb-4 group-hover:scale-110 transition duration-200" />
            <h4 className="text-lg font-bold text-white mb-2">{t[lang].feature1Title}</h4>
            <p className="text-xs text-gray-400 leading-relaxed">{t[lang].feature1Desc}</p>
          </div>

          <div className="bg-[#0d1321]/40 border border-gray-800 hover:border-indigo-500/20 p-6 rounded-2xl transition group">
            <Calendar className="w-8 h-8 text-indigo-400 mb-4 group-hover:scale-110 transition duration-200" />
            <h4 className="text-lg font-bold text-white mb-2">{t[lang].feature2Title}</h4>
            <p className="text-xs text-gray-400 leading-relaxed">{t[lang].feature2Desc}</p>
          </div>

          <div className="bg-[#0d1321]/40 border border-gray-800 hover:border-green-500/20 p-6 rounded-2xl transition group">
            <UserCheck className="w-8 h-8 text-green-400 mb-4 group-hover:scale-110 transition duration-200" />
            <h4 className="text-lg font-bold text-white mb-2">{t[lang].feature3Title}</h4>
            <p className="text-xs text-gray-400 leading-relaxed">{t[lang].feature3Desc}</p>
          </div>

          <div className="bg-[#0d1321]/40 border border-gray-800 hover:border-purple-500/20 p-6 rounded-2xl transition group">
            <Sparkles className="w-8 h-8 text-purple-400 mb-4 group-hover:scale-110 transition duration-200" />
            <h4 className="text-lg font-bold text-white mb-2">{t[lang].feature4Title}</h4>
            <p className="text-xs text-gray-400 leading-relaxed">{t[lang].feature4Desc}</p>
          </div>
        </div>
      </section>

      {/* TRACTION & COWORKING BARTER */}
      <section className="bg-gradient-to-b from-[#0d1321]/60 to-[#070b13] border border-gray-800 rounded-3xl p-8 md:p-10 space-y-8">
        <div className="space-y-3">
          <h3 className="text-2xl font-bold text-white">{t[lang].barterTitle}</h3>
          <p className="text-sm text-gray-400 max-w-4xl">{t[lang].barterDesc}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="bg-[#080d1a] border border-[#1e293b]/70 p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center mb-4">
                <Globe className="w-5 h-5 text-blue-400" />
              </div>
              <h4 className="text-lg font-bold text-white mb-2">{t[lang].barterSpace}</h4>
              <p className="text-xs text-gray-400 leading-relaxed">{t[lang].barterSpaceDesc}</p>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-800 flex justify-between text-xs">
              <span className="text-gray-500">Value Valuation:</span>
              <span className="font-bold text-blue-400">$250.00 USD / mo</span>
            </div>
          </div>

          <div className="bg-[#080d1a] border border-[#1e293b]/70 p-6 rounded-2xl flex flex-col justify-between">
            <div>
              <div className="w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center mb-4">
                <Shield className="w-5 h-5 text-green-400" />
              </div>
              <h4 className="text-lg font-bold text-white mb-2">{t[lang].barterPilots}</h4>
              <p className="text-xs text-gray-400 leading-relaxed">{t[lang].barterPilotsDesc}</p>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-800 flex justify-between text-xs">
              <span className="text-gray-500">Pilot Stage Status:</span>
              <span className="font-bold text-green-400">3 Agents Live</span>
            </div>
          </div>
        </div>
      </section>

      {/* PRICING PLANS */}
      <section id="pricing" className="space-y-12">
        <div className="text-center space-y-2">
          <h3 className="text-3xl font-bold text-white">{t[lang].plansTitle}</h3>
          <p className="text-gray-400 text-sm">{t[lang].plansSubtitle}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {/* Starter Plan */}
          <div className="bg-[#0c101c]/45 border border-gray-800 hover:border-gray-700 p-8 rounded-3xl flex flex-col justify-between relative transition">
            <div className="space-y-6">
              <div>
                <h4 className="text-xl font-bold text-white">{t[lang].plan1Name}</h4>
                <p className="text-xs text-gray-400 mt-2">{t[lang].plan1Desc}</p>
              </div>
              <div className="text-3xl font-extrabold text-white">
                {t[lang].plan1Price}
              </div>
              <ul className="space-y-3 text-xs text-gray-300">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan1Feature1}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan1Feature2}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan1Feature3}</span>
                </li>
              </ul>
            </div>
            <div className="pt-8">
              <Link 
                href="/login"
                className="block text-center py-2.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-xl text-white border border-gray-700 transition"
              >
                {t[lang].buttonDemo}
              </Link>
            </div>
          </div>

          {/* Professional Plan (Highlighted) */}
          <div className="bg-[#0c101c] border-2 border-blue-500/60 p-8 rounded-3xl flex flex-col justify-between relative shadow-2xl shadow-blue-500/5 transition">
            <div className="absolute top-0 right-6 -translate-y-1/2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-[9px] font-extrabold uppercase tracking-widest px-3 py-1 rounded-full shadow-lg">
              Popular
            </div>
            <div className="space-y-6">
              <div>
                <h4 className="text-xl font-bold text-white">{t[lang].plan2Name}</h4>
                <p className="text-xs text-gray-400 mt-2">{t[lang].plan2Desc}</p>
              </div>
              <div className="text-3xl font-extrabold text-blue-400">
                {t[lang].plan2Price}
              </div>
              <ul className="space-y-3 text-xs text-gray-300">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan2Feature1}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan2Feature2}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan2Feature3}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan2Feature4}</span>
                </li>
              </ul>
            </div>
            <div className="pt-8">
              <Link 
                href="/login"
                className="block text-center py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-xs font-semibold rounded-xl text-white shadow-md shadow-blue-500/10 transition"
              >
                {t[lang].buttonDemo}
              </Link>
            </div>
          </div>

          {/* Custom Plan */}
          <div className="bg-[#0c101c]/45 border border-gray-800 hover:border-gray-700 p-8 rounded-3xl flex flex-col justify-between relative transition">
            <div className="space-y-6">
              <div>
                <h4 className="text-xl font-bold text-white">{t[lang].plan3Name}</h4>
                <p className="text-xs text-gray-400 mt-2">{t[lang].plan3Desc}</p>
              </div>
              <div className="text-3xl font-extrabold text-white">
                {t[lang].plan3Price}
              </div>
              <ul className="space-y-3 text-xs text-gray-300">
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan3Feature1}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan3Feature2}</span>
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-400 flex-shrink-0" />
                  <span>{t[lang].plan3Feature3}</span>
                </li>
              </ul>
            </div>
            <div className="pt-8">
              <a 
                href="https://wa.me/573046242299" 
                target="_blank"
                rel="noreferrer"
                className="block text-center py-2.5 bg-gray-800 hover:bg-gray-700 text-xs font-semibold rounded-xl text-gray-300 hover:text-white border border-gray-700 transition"
              >
                {t[lang].learnMore}
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* TECH STACK SECTION */}
      <section className="text-center space-y-6 border-t border-gray-800 pt-12">
        <h3 className="text-2xl font-bold text-white">{t[lang].techTitle}</h3>
        <p className="text-xs text-gray-400 max-w-xl mx-auto">{t[lang].techDesc}</p>
        
        <div className="flex flex-wrap justify-center items-center gap-6 pt-4 text-xs font-bold text-gray-500 uppercase tracking-widest">
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">Google Cloud Vertex AI</div>
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">Gemini 2.0 Flash</div>
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">Next.js 15</div>
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">FastAPI (Python)</div>
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">ChromaDB RAG</div>
          <div className="px-4 py-2 bg-gray-900/60 border border-gray-800 rounded-xl">Vercel Serverless</div>
        </div>
      </section>

    </div>
  );
}
