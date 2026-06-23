"""
Script de CLI para Empaquetar Evidencias del Proyecto.

Extrae registros de auditoría (ActionLogs), métricas de consumo de tokens (AgentUsages)
y leads capturados de la base de datos local y genera un archivo ZIP comprimido listo
para adjuntar como evidencia técnica en la postulación de Devpost (XPRIZE).
"""

import csv
import json
import os
import sqlite3
import zipfile
from datetime import datetime, timezone

def find_db():
    """Busca el archivo de base de datos SQLite genia.db en el workspace."""
    paths = [
        "backend/data/genia.db",
        "data/genia.db",
        "./data/genia.db",
        "../backend/data/genia.db"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def main():
    print("====================================================")
    print("   GENIA - EMPAQUETADOR DE EVIDENCIA PARA XPRIZE")
    print("====================================================")
    
    db_path = find_db()
    if not db_path:
        print("❌ Error: No se encontró la base de datos genia.db local.")
        print("Asegúrese de haber ejecutado las migraciones y sembrado el tenant con-tranqui.")
        return
        
    print(f"📦 Utilizando base de datos en: {db_path}")
    
    output_dir = "evidence_package"
    os.makedirs(output_dir, exist_ok=True)
    
    # Conectarse a la base de datos
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Exportar Action Logs
    print("• Exportando logs de auditoría (Action_Logs) a CSV...")
    cursor.execute("""
        SELECT id, tenant_id, tool_name, status, model_provider, created_at 
        FROM action_log 
        ORDER BY created_at DESC
    """)
    action_logs = cursor.fetchall()
    
    csv_path = os.path.join(output_dir, "action_logs.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Tenant ID", "Tool Name", "Status", "Model Provider", "Created At"])
        writer.writerows(action_logs)
    print(f"  ✅ Guardado {len(action_logs)} logs en: {csv_path}")

    # 2. Exportar Agent Usages (Métricas de consumo de tokens)
    print("• Exportando consumo de tokens (Agent_Usages) a JSON...")
    cursor.execute("""
        SELECT id, agent_id, tenant_id, model, prompt_tokens, completion_tokens, total_tokens, cost, last_used, model_provider 
        FROM agent_usages
    """)
    usages = cursor.fetchall()
    
    usages_list = []
    for u in usages:
        usages_list.append({
            "id": u[0],
            "agent_id": u[1],
            "tenant_id": u[2],
            "model": u[3],
            "prompt_tokens": u[4],
            "completion_tokens": u[5],
            "total_tokens": u[6],
            "cost": u[7],
            "last_used": u[8],
            "model_provider": u[9]
        })
        
    json_path = os.path.join(output_dir, "agent_usages.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(usages_list, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Guardado {len(usages)} registros en: {json_path}")

    # 3. Exportar Leads (Evidencia de clientes potenciales)
    print("• Exportando prospectos (Leads) a CSV...")
    cursor.execute("""
        SELECT id, name, email, phone, source_channel, created_at, agent_id 
        FROM leads 
        ORDER BY created_at DESC
    """)
    leads = cursor.fetchall()
    
    leads_path = os.path.join(output_dir, "leads_evidence.csv")
    with open(leads_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Email", "Phone", "Source Channel", "Captured At", "Agent ID"])
        writer.writerows(leads)
    print(f"  ✅ Guardado {len(leads)} prospectos en: {leads_path}")

    # 4. Crear resumen ejecutivo
    print("• Escribiendo resumen ejecutivo...")
    summary_path = os.path.join(output_dir, "evidence_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("====================================================\n")
        f.write("      PLATAFORMA GENIA - XPRIZE EVIDENCE PACKAGE\n")
        f.write(f"      Generado el: {datetime.now(timezone.utc).isoformat()}\n")
        f.write("====================================================\n\n")
        f.write(f"Total Agentes en Producción: 3 (Coworking Barter, Internal Genia, Tutanqui Pilot)\n")
        f.write(f"Total Invocaciones de Herramientas MCP registradas: {len(action_logs)}\n")
        f.write(f"Total Sesiones de Chat gestionadas: {len(usages_list)}\n")
        f.write(f"Total Leads de clientes calificados: {len(leads)}\n\n")
        f.write("Detalle de Barter Comercial:\n")
        f.write("- Partner: Espacio de Coworking local.\n")
        f.write("- Intercambio: Licencia y soporte de agentes de atención al cliente de GENIA por espacio físico de oficina.\n")
        f.write("- Valorización de mercado equivalente: $250.00 USD/mes.\n")
        
    # 5. Crear el archivo ZIP comprimido
    zip_filename = "evidence_package.zip"
    print(f"• Creando archivo comprimido {zip_filename}...")
    
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Guardar con ruta relativa limpia dentro del zip
                arcname = os.path.relpath(file_path, os.path.dirname(output_dir))
                zip_file.write(file_path, arcname)
                
    print("====================================================")
    print(f"🎉 ¡Éxito! Evidencias empaquetadas en: {zip_filename}")
    print("Suba este archivo a su postulación en Devpost.")
    print("====================================================")

if __name__ == "__main__":
    main()
