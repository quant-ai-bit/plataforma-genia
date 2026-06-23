"""
Script unificado para ejecutar todas las pruebas de PLATAFORMA GENIA.
Ejecuta cada script de prueba en un subproceso y presenta un reporte consolidado.
"""

import sys
import os
import subprocess
import time

# Lista de scripts de prueba a ejecutar
TEST_SCRIPTS = [
    "test_mcp_integration.py",
    "test_deepseek_call.py",
    "test_openrouter.py",
    "test_kb_update.py",
    "test_images.py",
    "test_didactic_training.py",
    "test_rag.py",
    "test_new_features.py",
    "test_api.py"
]

def run_script(script_name):
    print(f"\n==================================================")
    print(f" Ejecutando: {script_name}")
    print(f"==================================================")
    
    python_exe = sys.executable
    start_time = time.time()
    
    # Ejecutar el script heredando stdout/stderr para ver logs en tiempo real
    process = subprocess.Popen([python_exe, script_name])
    process.communicate()
    
    elapsed = time.time() - start_time
    success = (process.returncode == 0)
    
    return success, elapsed

def main():
    print("==================================================")
    print(" INICIANDO EJECUCIÓN UNIFICADA DE PRUEBAS - PLATAFORMA GENIA")
    print("==================================================")
    
    results = {}
    total_start = time.time()
    
    for script in TEST_SCRIPTS:
        if not os.path.exists(script):
            print(f"[ADVERTENCIA] El archivo {script} no existe, se omitirá.")
            results[script] = ("OMITIDO", 0.0)
            continue
            
        success, elapsed = run_script(script)
        status = "PASADO" if success else "FALLADO"
        results[script] = (status, elapsed)
        
    total_elapsed = time.time() - total_start
    
    print("\n" + "=" * 60)
    print("               RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"{'Script de Prueba':<35} | {'Estado':<10} | {'Duración (s)':<10}")
    print("-" * 60)
    
    passed_count = 0
    failed_count = 0
    omitted_count = 0
    
    for script, (status, elapsed) in results.items():
        print(f"{script:<35} | {status:<10} | {elapsed:<10.2f}")
        if status == "PASADO":
            passed_count += 1
        elif status == "FALLADO":
            failed_count += 1
        else:
            omitted_count += 1
            
    print("-" * 60)
    print(f"Total: {len(TEST_SCRIPTS)} | Pasados: {passed_count} | Fallados: {failed_count} | Omitidos: {omitted_count}")
    print(f"Tiempo Total de Ejecución: {total_elapsed:.2f} segundos")
    print("=" * 60)
    
    if failed_count > 0:
        print("\n[ERROR] Algunas pruebas fallaron. Revisa los logs superiores.")
        sys.exit(1)
    else:
        print("\n[ÉXITO] ¡Todas las pruebas se ejecutaron y pasaron exitosamente!")
        sys.exit(0)

if __name__ == "__main__":
    main()
