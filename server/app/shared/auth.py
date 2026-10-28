import jwt

from app.shared.secrets import get_secret

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client

    if _jwks_client is not None:
        return _jwks_client

    supabase_url = get_secret("SUPABASE_URL")
    jwks_url     = f"{supabase_url}/auth/v1/.well-known/jwks.json"

    print(f"[Auth] Fetching JWKS from: {jwks_url}")

    _jwks_client = jwt.PyJWKClient(
        jwks_url,
        cache_keys=True,
    )

    print(f"[Auth] JWKS client initialised")
    return _jwks_client


def verify_supabase_jwt(token: str) -> dict:
    jwks_client = _get_jwks_client()

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_exp": True}
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise Exception("TOKEN_EXPIRED")

    except jwt.InvalidAudienceError:
        raise Exception("TOKEN_INVALID_AUDIENCE")

    except jwt.DecodeError:
        raise Exception("TOKEN_MALFORMED")

    except jwt.InvalidTokenError as e:
        raise Exception(f"TOKEN_INVALID: {str(e)}")

    except Exception as e:
        raise Exception(f"AUTH_ERROR: {str(e)}")


def get_user_from_token(authorization: str | None) -> dict:
    auth_header = authorization or ""

    if not auth_header.startswith("Bearer "):
        raise Exception("MISSING_AUTH_HEADER")

    token = auth_header[7:]

    if not token:
        raise Exception("EMPTY_TOKEN")

    payload = verify_supabase_jwt(token)

    return {
        "user_id": payload["sub"],
        "email":   payload.get("email"),
        "role":    payload.get("role"),
    }
