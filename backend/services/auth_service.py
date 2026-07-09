"""
Servicio de Autenticación de PLATAFORMA GENIA.

Permite verificar los tokens JWT emitidos por Supabase en las peticiones HTTP.
Provee una dependencia inyectable para proteger los endpoints de FastAPI.
"""

import logging
import jwt
import base64
import httpx
import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

logger = logging.getLogger(__name__)

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configuración del esquema Bearer HTTP
security = HTTPBearer(auto_error=False)

def verify_token_via_supabase_api(token: str) -> dict | None:
    supabase_url = getattr(settings, "supabase_url", "")
    anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or getattr(settings, "supabase_service_key", "") or "sb_publishable_Ceu7xc_zhyotWO9lkWBJKg_oUrkw8D3"
    
    if not supabase_url:
        print("[AUTH_DEBUG] Supabase URL not configured for API fallback verification")
        return None
        
    try:
        print(f"[AUTH_DEBUG] Attempting token verification via Supabase Auth API: {supabase_url}/auth/v1/user")
        headers = {
            "apikey": anon_key,
            "Authorization": f"Bearer {token}"
        }
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{supabase_url}/auth/v1/user", headers=headers)
            
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("id")
            email = user_data.get("email")
            print(f"[AUTH_DEBUG] Supabase Auth API verification succeeded. User ID: {user_id}")
            return {
                "id": user_id,
                "email": email
            }
        else:
            print(f"[AUTH_DEBUG] Supabase Auth API verification failed. Status code: {response.status_code}")
    except Exception as e:
        print(f"[AUTH_DEBUG] Exception during Supabase Auth API verification: {str(e)}")
        
    return None

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependencia de FastAPI para obtener y validar el usuario actual de Supabase
    a partir del token JWT enviado en la cabecera Authorization.
    
    Retorna:
        dict: Información del usuario (id, email).
    """
    jwt_secret = getattr(settings, "supabase_jwt_secret", "")
    
    # Decodificar el secret de Supabase si es un hash base64
    secret_key = jwt_secret
    if jwt_secret:
        try:
            secret_key = base64.b64decode(jwt_secret)
        except Exception as e:
            print(f"[AUTH_DEBUG] No se pudo decodificar SUPABASE_JWT_SECRET en base64, usando string original: {str(e)}")
    
    print(f"[AUTH_DEBUG] get_current_user called. Credentials present: {credentials is not None}")

    if not credentials:
        if ENVIRONMENT == "development":
            print("[AUTH_DEBUG] No credentials provided, using local_dev_user because ENVIRONMENT is development")
            return {"id": "local_dev_user", "email": "dev@genia.local"}
            
        print("[AUTH_DEBUG] No credentials provided, raising 401")
        raise HTTPException(
            status_code=401,
            detail="Autenticación requerida. Token de sesión no encontrado.",
        )
    
    token = credentials.credentials
    
    try:
        unverified_headers = jwt.get_unverified_header(token)
        print(f"[AUTH_DEBUG] Token unverified headers: {unverified_headers}")
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            print(f"[AUTH_DEBUG] Unverified token payload: {unverified_payload}")
        except Exception as e:
            print(f"[AUTH_DEBUG] Failed to decode unverified payload: {str(e)}")
        
        is_hs256 = unverified_headers.get("alg") == "HS256"
        
        if jwt_secret and is_hs256:
            payload = None
            verification_errors = []
            
            # Intento 1: Usar la clave decodificada en base64
            if secret_key:
                try:
                    print("[AUTH_DEBUG] Attempting verification with base64-decoded key...")
                    payload = jwt.decode(
                        token,
                        secret_key,
                        algorithms=["HS256"],
                        options={"verify_aud": True},
                        audience="authenticated",
                    )
                    print("[AUTH_DEBUG] Verification succeeded with base64-decoded key.")
                except jwt.InvalidTokenError as e:
                    print(f"[AUTH_DEBUG] Verification failed with base64-decoded key: {str(e)}")
                    verification_errors.append(f"base64-decoded: {str(e)}")
            
            # Intento 2: Usar la clave como cadena de texto cruda (raw string bytes)
            if payload is None and jwt_secret:
                try:
                    print("[AUTH_DEBUG] Attempting verification with raw string key...")
                    raw_key = jwt_secret.encode('utf-8') if isinstance(jwt_secret, str) else jwt_secret
                    payload = jwt.decode(
                        token,
                        raw_key,
                        algorithms=["HS256"],
                        options={"verify_aud": True},
                        audience="authenticated",
                    )
                    print("[AUTH_DEBUG] Verification succeeded with raw string key.")
                except jwt.InvalidTokenError as e:
                    print(f"[AUTH_DEBUG] Verification failed with raw string key: {str(e)}")
                    verification_errors.append(f"raw-string: {str(e)}")
            
            # Si ambos fallaron localmente, intentar la API de Supabase
            if payload is None:
                api_user = verify_token_via_supabase_api(token)
                if api_user:
                    return api_user
                    
                # Si la API también falló
                if ENVIRONMENT == "development":
                    print("[AUTH_DEBUG] HS256 verification and API verification failed, but ENVIRONMENT is development. Falling back to unverified decode.")
                    payload = jwt.decode(token, options={"verify_signature": False})
                else:
                    print(f"[AUTH_DEBUG] HS256 verification failed for all keys. Errors: {verification_errors}")
                    raise jwt.InvalidTokenError(f"Signature verification failed for all keys: {verification_errors}")
        else:
            # Si no es HS256 o no hay secreto
            payload = None
            
            # Intentar verificar contra la API de Supabase
            api_user = verify_token_via_supabase_api(token)
            if api_user:
                return api_user
                
            if ENVIRONMENT == "development":
                print(f"[AUTH_DEBUG] Token algorithm is {unverified_headers.get('alg')} and ENVIRONMENT is development. Decoding WITHOUT signature verification.")
                payload = jwt.decode(token, options={"verify_signature": False})
            else:
                if not jwt_secret:
                    print("[AUTH_DEBUG] Error: SUPABASE_JWT_SECRET not configured in non-dev environment")
                    raise HTTPException(
                        status_code=500,
                        detail="Error de configuración: SUPABASE_JWT_SECRET no configurada en producción.",
                    )
                else:
                    print(f"[AUTH_DEBUG] Error: Unsupported token algorithm {unverified_headers.get('alg')} in production")
                    raise HTTPException(
                        status_code=401,
                        detail=f"Algoritmo de token no soportado en producción: {unverified_headers.get('alg')}.",
                    )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        print(f"[AUTH_DEBUG] Token decoded successfully. user_id: {user_id}, email: {email}")
        
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
        print(f"[AUTH_DEBUG] Token de sesión expirado: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="La sesión ha expirado. Por favor, inicia sesión de nuevo.",
        )
    except jwt.InvalidTokenError as e:
        print(f"[AUTH_DEBUG] Error de validación de token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Token de sesión no válido: {str(e)}",
        )
