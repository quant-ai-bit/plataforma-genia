"""
Servicio de Autenticación de PLATAFORMA GENIA.

Permite verificar los tokens JWT emitidos por Supabase en las peticiones HTTP.
Provee una dependencia inyectable para proteger los endpoints de FastAPI.
"""

import logging
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

logger = logging.getLogger(__name__)

import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configuración del esquema Bearer HTTP
security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependencia de FastAPI para obtener y validar el usuario actual de Supabase
    a partir del token JWT enviado en la cabecera Authorization.
    
    Retorna:
        dict: Información del usuario (id, email).
    """
    from datetime import datetime
    jwt_secret = getattr(settings, "supabase_jwt_secret", "")
    
    with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] --- get_current_user called ---\n")
        f.write(f"Credentials present: {credentials is not None}\n")
        if credentials:
            f.write(f"Token length: {len(credentials.credentials)}\n")
            f.write(f"JWT Secret configured: {bool(jwt_secret)}\n")

    if not credentials:
        if not jwt_secret and ENVIRONMENT == "development":
            with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                f.write("No credentials provided, using local_dev_user because jwt_secret is empty and ENVIRONMENT is development\n")
            return {"id": "local_dev_user", "email": "dev@genia.local"}
            
        with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
            f.write("No credentials provided, raising 401\n")
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida. Token de sesión no encontrado.",
        )
    
    token = credentials.credentials
    
    try:
        unverified_headers = jwt.get_unverified_header(token)
        with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Token unverified headers: {unverified_headers}\n")
        
        is_hs256 = unverified_headers.get("alg") == "HS256"
        
        if jwt_secret and is_hs256:
            try:
                with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Decoding token WITH signature verification (HS256), secret starts with: {jwt_secret[:10]}...\n")
                payload = jwt.decode(
                    token,
                    jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": True},
                    audience="authenticated",
                )
            except jwt.InvalidTokenError as e:
                if ENVIRONMENT == "development":
                    with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"HS256 verification failed ({str(e)}), but ENVIRONMENT is development. Falling back to unverified decode.\n")
                    payload = jwt.decode(token, options={"verify_signature": False})
                else:
                    raise
        else:
            # Si no es HS256 o no hay secreto
            if ENVIRONMENT == "development":
                with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Token algorithm is {unverified_headers.get('alg')} and ENVIRONMENT is development. Decoding WITHOUT signature verification.\n")
                payload = jwt.decode(token, options={"verify_signature": False})
            else:
                if not jwt_secret:
                    with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                        f.write("Error: SUPABASE_JWT_SECRET not configured in non-dev environment\n")
                    raise HTTPException(
                        status_code=500,
                        detail="Error de configuración: SUPABASE_JWT_SECRET no configurada en producción.",
                    )
                else:
                    with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"Error: Unsupported token algorithm {unverified_headers.get('alg')} in production\n")
                    raise HTTPException(
                        status_code=401,
                        detail=f"Algoritmo de token no soportado en producción: {unverified_headers.get('alg')}.",
                    )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
            f.write(f"Token decoded successfully. user_id: {user_id}, email: {email}\n")
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token no válido: falta el campo sub (User ID).",
            )
            
        return {
            "id": user_id,
            "email": email,
        }
        
    except jwt.ExpiredSignatureError as e:
        with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
            f.write(f"ExpiredSignatureError: {str(e)}\n")
        logger.warning("Token de sesión expirado.")
        raise HTTPException(
            status_code=401,
            detail="La sesión ha expirado. Por favor, inicia sesión de nuevo.",
        )
    except jwt.InvalidTokenError as e:
        with open("C:/Users/User/Desktop/ANTIGRAVITY/PLATAFORMA GENIA/backend/data/auth_debug.log", "a", encoding="utf-8") as f:
            f.write(f"InvalidTokenError: {str(e)}\n")
        logger.warning(f"Error de validación de token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Token de sesión no válido: {str(e)}",
        )
