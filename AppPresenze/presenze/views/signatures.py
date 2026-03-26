from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import hashlib

from ..models import Signature, SignatureEvent
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


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def signature_create(request):
    target_user, error_response = _resolve_target_user(request)
    if error_response is not None:
        return error_response

    file = request.FILES.get("file")
    if file is None:
        return Response(
            {"error": "Campo 'file' obbligatorio.", "code": "SIGNATURE_FILE_REQUIRED"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    allowed_mime = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/bmp",
        "image/gif",
    }
    mime_type = (getattr(file, "content_type", "") or "").lower()
    if mime_type not in allowed_mime:
        return Response(
            {
                "error": "Formato firma non supportato. Usa PNG, JPG/JPEG, WEBP, BMP o GIF.",
                "code": "SIGNATURE_FILE_TYPE",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if file.size and int(file.size) > 10 * 1024 * 1024:
        return Response(
            {"error": "File troppo grande (max 10MB).", "code": "SIGNATURE_FILE_SIZE"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    image_bytes = file.read()
    if not image_bytes:
        return Response(
            {"error": "File firma vuoto.", "code": "SIGNATURE_FILE_EMPTY"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sha256 = hashlib.sha256(image_bytes).hexdigest()
    signature = Signature.objects.filter(user_id=target_user.id).order_by("-updated_at", "-created_at").first()
    if signature is None:
        signature = Signature.objects.create(
            user=target_user,
            image_data=image_bytes,
            mime_type=mime_type,
            file_name=file.name or "",
            svg=None,
            sha256=sha256,
            width=None,
            height=None,
        )
    else:
        signature.image_data = image_bytes
        signature.mime_type = mime_type
        signature.file_name = file.name or ""
        signature.svg = None
        signature.sha256 = sha256
        signature.width = None
        signature.height = None
        signature.save(
            update_fields=[
                "image_data",
                "mime_type",
                "file_name",
                "svg",
                "sha256",
                "width",
                "height",
                "updated_at",
            ]
        )

    Signature.objects.filter(user_id=target_user.id).exclude(pk=signature.pk).delete()

    SignatureEvent.objects.create(
        signature=signature,
        user=request.user,
        event_type=SignatureEvent.EventType.CREATED,
        ip_address=_get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )
    return Response(SignatureSerializer(signature).data, status=status.HTTP_201_CREATED)


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
