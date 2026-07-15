from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import JiraReference
from ..serializer import (
    JiraReferenceDeleteSerializer,
    JiraReferenceSerializer,
    JiraReferenceUpdateSerializer,
)


def _as_item_list(payload):
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items", [payload])
    else:
        raise ValidationError({"detail": "Il payload deve essere un oggetto o una lista di elementi."})

    if not isinstance(items, list) or not items:
        raise ValidationError({"items": "Inserisci almeno un elemento."})
    return items


class JiraReferenceGetView(APIView):
    """GET /jira/reference/get/ -> lista dei riferimenti prezzo Jira."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        references = JiraReference.objects.all().order_by("name", "id")
        return Response(JiraReferenceSerializer(references, many=True).data)


class JiraReferenceAddView(APIView):
    """POST /jira/reference/add/ -> crea uno o piu riferimenti."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = JiraReferenceSerializer(data=_as_item_list(request.data), many=True)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            references = serializer.save()

        return Response(
            {"count": len(references), "items": JiraReferenceSerializer(references, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class JiraReferencePutView(APIView):
    """PUT /jira/reference/put/ -> aggiorna uno o piu riferimenti."""

    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = JiraReferenceUpdateSerializer(data=_as_item_list(request.data), many=True)
        serializer.is_valid(raise_exception=True)
        updates = serializer.validated_data
        ids = [item["id"] for item in updates]

        if len(ids) != len(set(ids)):
            raise ValidationError({"items": "Ogni id puo comparire una sola volta."})

        references_by_id = JiraReference.objects.in_bulk(ids)
        missing_ids = [reference_id for reference_id in ids if reference_id not in references_by_id]
        if missing_ids:
            return Response(
                {"detail": "Alcuni riferimenti non esistono.", "missing_ids": missing_ids},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            for update in updates:
                reference = references_by_id[update["id"]]
                update_fields = []
                for field in ("name", "price"):
                    if field in update:
                        setattr(reference, field, update[field])
                        update_fields.append(field)
                reference.save(update_fields=update_fields)

        references = [references_by_id[reference_id] for reference_id in ids]
        return Response({"count": len(references), "items": JiraReferenceSerializer(references, many=True).data})


class JiraReferenceDeleteView(APIView):
    """DELETE /jira/reference/delete/ -> elimina uno o piu riferimenti."""

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        if isinstance(request.data, dict):
            payload = request.data
            if "ids" not in payload and "id" in payload:
                payload = {"ids": [payload["id"]]}
        else:
            payload = {"ids": request.data}
        serializer = JiraReferenceDeleteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        ids = list(dict.fromkeys(serializer.validated_data["ids"]))

        references = JiraReference.objects.filter(id__in=ids)
        found_ids = set(references.values_list("id", flat=True))
        missing_ids = [reference_id for reference_id in ids if reference_id not in found_ids]
        if missing_ids:
            return Response(
                {"detail": "Alcuni riferimenti non esistono.", "missing_ids": missing_ids},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            deleted_count, _ = references.delete()

        return Response({"count": deleted_count, "deleted_ids": ids}, status=status.HTTP_200_OK)
