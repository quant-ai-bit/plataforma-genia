"""Test de integración MCP para PLATAFORMA GENIA."""
import sys
sys.path.insert(0, ".")

# 1. Test importaciones
from services.mcp_adapter import mcp_tools_to_function_calling
from services.mcp_builtin_server import get_builtin_tools, is_builtin_tool
from services.mcp_registry import mcp_registry
from services.mcp_client import mcp_client_manager
from models.mcp_server_config import MCPServerConfig

print("[OK] Todas las importaciones de MCP exitosas.")

# 2. Test built-in tools con custom fields
custom_fields = [
    {"key": "email", "type": "string", "description": "Email del lead"},
    {"key": "phone", "type": "string", "description": "Teléfono del lead"},
    {"key": "company", "type": "string", "description": "Empresa del lead"},
]
tools = get_builtin_tools(custom_fields)
print(f"[OK] Built-in tools generados: {len(tools)}")
for t in tools:
    print(f"     - {t['name']}: {len(t['inputSchema'].get('properties', {}))} propiedades")

# 3. Test adapter MCP → function-calling
fc_tools = mcp_tools_to_function_calling(tools)
print(f"[OK] Adaptados a function-calling: {len(fc_tools)}")
for t in fc_tools:
    fn = t["function"]
    print(f"     - {fn['name']}: {len(fn['parameters'].get('properties', {}))} params")

# 4. Test is_builtin_tool
assert is_builtin_tool("save_lead_info") == True
assert is_builtin_tool("trigger_human_handoff") == True
assert is_builtin_tool("some_external_tool") == False
print("[OK] is_builtin_tool funciona correctamente.")

# 5. Test async execute_builtin_tool
import asyncio
from services.mcp_builtin_server import execute_builtin_tool

async def test_execute():
    r1 = await execute_builtin_tool("save_lead_info", {"name": "Test User"})
    assert "result" in r1
    print(f"[OK] execute_builtin_tool save_lead_info: {r1}")

    r2 = await execute_builtin_tool("trigger_human_handoff", {})
    assert "result" in r2
    print(f"[OK] execute_builtin_tool trigger_human_handoff: {r2}")

    r3 = await execute_builtin_tool("alert_owner_about_unanswered_query", {"unanswered_question": "Precio?"})
    assert "result" in r3
    print(f"[OK] execute_builtin_tool alert_unanswered: {r3}")

asyncio.run(test_execute())

# 6. Verificar que el modelo SQL se genera correctamente
print(f"[OK] MCPServerConfig tablename: {MCPServerConfig.__tablename__}")

print("\n" + "=" * 60)
print("  [PASS] TODOS LOS TESTS DE MCP PASARON EXITOSAMENTE")
print("=" * 60)
