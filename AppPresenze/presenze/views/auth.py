from django.contrib.auth import authenticate, logout
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from ..serializer import UtenteSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    return _issue_token_response(request)

@api_view(['POST'])
@permission_classes([AllowAny])
def get_token(request):
    return _issue_token_response(request)

def _issue_token_response(request):
    """Rilascia un Bearer token (DRF Token) a fronte di email/password.
    Body: { "email": "...", "password": "..." } o { "username": "...", "password": "..." }
    Ritorna: { "token": "...", "token_type": "Bearer", "user": { ... } }
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
            status=status.HTTP_400_BAD_REQUEST,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "token_type": "Bearer",
        "user": UtenteSerializer(user).data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """Logout della sessione corrente."""
    logout(request)
    request.user.auth_token.delete() # Con questa riga viene rimosso anche il token presente a DB e l'utente fa logout da qualsiasi client
    return Response({"message": "Logout effettuato"})