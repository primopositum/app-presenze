from django.contrib.auth import authenticate, logout
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from ..serializer import UtenteSerializer


def _cookie_cfg():
    return {
        "access_name": settings.SIMPLE_JWT.get("AUTH_COOKIE", "access_token"),
        "refresh_name": settings.SIMPLE_JWT.get("AUTH_COOKIE_REFRESH", "refresh_token"),
        "secure": bool(settings.SIMPLE_JWT.get("AUTH_COOKIE_SECURE", not settings.DEBUG)),
        "httponly": bool(settings.SIMPLE_JWT.get("AUTH_COOKIE_HTTP_ONLY", True)),
        "samesite": settings.SIMPLE_JWT.get("AUTH_COOKIE_SAMESITE", "Lax"),
        "path": settings.SIMPLE_JWT.get("AUTH_COOKIE_PATH", "/"),
    }


def _set_auth_cookies(response: Response, access: str, refresh: str | None = None):
    cfg = _cookie_cfg()
    response.set_cookie(
        cfg["access_name"],
        access,
        httponly=cfg["httponly"],
        secure=cfg["secure"],
        samesite=cfg["samesite"],
        path=cfg["path"],
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
    )
    if refresh is not None:
        response.set_cookie(
            cfg["refresh_name"],
            refresh,
            httponly=cfg["httponly"],
            secure=cfg["secure"],
            samesite=cfg["samesite"],
            path=cfg["path"],
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        )


def _clear_auth_cookies(response: Response):
    cfg = _cookie_cfg()
    response.delete_cookie(cfg["access_name"], path=cfg["path"], samesite=cfg["samesite"])
    response.delete_cookie(cfg["refresh_name"], path=cfg["path"], samesite=cfg["samesite"])


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    return _issue_token_response(request)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_token(request):
    return _issue_token_response(request)

def _issue_token_response(request):
    """Login JWT: imposta access+refresh token in cookie HttpOnly.
    Body: { "email": "...", "password": "..." } o { "username": "...", "password": "..." }
    Ritorna: { "token_type": "Bearer", "user": { ... } }
    """
    email = request.data.get("email")
    username = request.data.get("username")
    password = request.data.get("password")

    login_username = email or username
    if not login_username or not password:
        return Response(
            {"error": "Email/username e password sono obbligatori"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=login_username, password=password)
    if user is None or not user.is_active:
        return Response(
            {"error": "Credenziali non valide"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    response = Response({
        "token_type": "Bearer",
        "user": UtenteSerializer(user).data,
    })
    _set_auth_cookies(response, access=access, refresh=str(refresh))
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def api_refresh(request):
    cfg = _cookie_cfg()
    refresh_token = request.COOKIES.get(cfg["refresh_name"]) or request.data.get("refresh")
    if not refresh_token:
        return Response({"error": "Refresh token mancante"}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
    try:
        serializer.is_valid(raise_exception=True)
    except Exception:
        return Response({"error": "Refresh token non valido"}, status=status.HTTP_401_UNAUTHORIZED)

    access = serializer.validated_data["access"]
    new_refresh = serializer.validated_data.get("refresh")
    response = Response({"message": "Token aggiornato"})
    _set_auth_cookies(response, access=access, refresh=new_refresh)
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """Logout: invalida refresh token (best effort) e pulisce i cookie."""
    cfg = _cookie_cfg()
    refresh_token = request.COOKIES.get(cfg["refresh_name"]) or request.data.get("refresh")
    if refresh_token:
        try:
            RefreshToken(refresh_token).blacklist()
        except Exception:
            pass
    logout(request)
    response = Response({"message": "Logout effettuato"})
    _clear_auth_cookies(response)
    return response
