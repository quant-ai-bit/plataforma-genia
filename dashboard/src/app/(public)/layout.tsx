import React from "react";

export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#070b13] text-gray-100 flex flex-col">
      {/* Header simple para jueces */}
      <header className="h-20 border-b border-[#1e293b] bg-[#0c101c]/45 flex items-center justify-between px-8 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-blue-500 to-purple-600 rounded-lg shadow-lg">
            <span className="text-white font-extrabold text-sm tracking-wider">G</span>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-500 bg-clip-text text-transparent">
              GENIA
            </h1>
            <span className="text-[10px] text-gray-500 tracking-widest font-semibold block uppercase">
              AI Agents Platform
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col">
        {children}
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-[#1e293b] bg-[#070b13] text-center text-xs text-gray-500">
        <p>© 2026 GENIA – Tecnología inteligente que trabaja para ti. Colombia</p>
      </footer>
    </div>
  );
}
