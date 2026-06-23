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
    jwt_secret = getattr(settings, "supabase_jwt_secret", "")
    
    if not credentials:
        if not jwt_secret and ENVIRONMENT == "development":
            # Si no hay secreto de Supabase (local dev) y no se envía token,
            # permitimos pasar con un usuario dummy para no bloquear las pruebas locales.
            return {"id": "local_dev_user", "email": "dev@genia.local"}
            
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida. Token de sesión no encontrado.",
        )
    
    token = credentials.credentials
    
    try:
        if not jwt_secret:
            if ENVIRONMENT == "development":
                # En modo de desarrollo local si no se configura la llave secreta,
                # decodificamos el payload del token sin verificar la firma para simplificar las pruebas.
                logger.warning(
                    "SUPABASE_JWT_SECRET no configurada. Decodificando token sin verificar firma (solo desarrollo local)."
                )
                payload = jwt.decode(token, options={"verify_signature": False})
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Error de configuración: SUPABASE_JWT_SECRET no configurada en producción.",
                )
        else:
            # Verificación estándar de Supabase HS256
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": True},
                audience="authenticated",
            )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="Token no válido: falta el campo sub (User ID).",
            )
            
        return {
            "id": user_id,
            "email": email,
        }
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token de sesión expirado.")
        raise HTTPException(
            status_code=401,
            detail="La sesión ha expirado. Por favor, inicia sesión de nuevo.",
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Error de validación de token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Token de sesión no válido: {str(e)}",
        )
