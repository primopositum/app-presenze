from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Signature
from ..serializer import SignatureSerializer


def _resolve_target_user(request):
    raw = request.query_params.get("u_id") or request.query_params.get("user_id")
    if raw in (None, "") and hasattr(request, "data"):
        raw = request.data.get("u_id") or request.data.get("user_id")

    if raw in (None, ""):
        return request.user, None

    try:
        target_id = int(raw)
    except (TypeError, ValueError):
        return None, Response({"errors": "u_id/user_id non valido."}, status=status.HTTP_400_BAD_REQUEST)

    if not request.user.is_superuser and request.user.id != target_id:
        return None, Response({"errors": "Non hai i permessi per questa firma."}, status=status.HTTP_403_FORBIDDEN)

    from ..models import Utente

    try:
        return Utente.objects.get(pk=target_id), None
    except Utente.DoesNotExist:
        return None, Response({"errors": "Utente non trovato."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def signature_create(request):
    target_user, error_response = _resolve_target_user(request)
    if error_response is not None:
        return error_response

    serializer = SignatureSerializer(
        data=request.data,
        context={"request": request, "target_user": target_user}
    )
    if serializer.is_valid():
        signature = serializer.save()
        return Response(SignatureSerializer(signature).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def signature_latest(request):
    target_user, error_response = _resolve_target_user(request)
    if error_response is not None:
        return error_response

    signature = Signature.objects.filter(user_id=target_user.id).order_by("-updated_at", "-created_at").first()
    if signature is None:
        return Response({"signature": None}, status=status.HTTP_200_OK)

    return Response(SignatureSerializer(signature).data, status=status.HTTP_200_OK)
