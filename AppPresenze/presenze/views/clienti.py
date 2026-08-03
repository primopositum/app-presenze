from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Cliente, ContrattoCliente
from ..serializer import ClienteSerializer, ContrattoClienteSerializer


class ClienteListCreateView(ListCreateAPIView):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]


class ClienteDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        cliente = self.get_object()
        if cliente.contratti_commerciali.exists():
            return Response(
                {"detail": "Non puoi eliminare un cliente con contratti commerciali associati."},
                status=status.HTTP_409_CONFLICT,
            )
        cliente.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContrattoClienteListCreateView(ListCreateAPIView):
    queryset = ContrattoCliente.objects.select_related("cliente")
    serializer_class = ContrattoClienteSerializer
    permission_classes = [IsAuthenticated]


class ContrattoClienteDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ContrattoCliente.objects.select_related("cliente")
    serializer_class = ContrattoClienteSerializer
    permission_classes = [IsAuthenticated]


class ContrattoClientePoolTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_contratto(self, pk):
        try:
            return ContrattoCliente.objects.select_related("cliente").get(pk=pk)
        except ContrattoCliente.DoesNotExist:
            return None

    @staticmethod
    def _task_from_request(request):
        task = request.data.get("task")
        task = task.strip() if isinstance(task, str) else ""
        return task

    def post(self, request, pk):
        contratto = self._get_contratto(pk)
        if contratto is None:
            return Response({"detail": "Contratto commerciale non trovato."}, status=status.HTTP_404_NOT_FOUND)

        task = self._task_from_request(request)
        if not task:
            return Response({"task": "Task obbligatoria."}, status=status.HTTP_400_BAD_REQUEST)

        pool_task = list(contratto.pool_task or [])
        if task not in pool_task:
            pool_task.append(task)
            contratto.pool_task = pool_task
            contratto.full_clean()
            contratto.save(update_fields=["pool_task"])

        return Response(ContrattoClienteSerializer(contratto).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        contratto = self._get_contratto(pk)
        if contratto is None:
            return Response({"detail": "Contratto commerciale non trovato."}, status=status.HTTP_404_NOT_FOUND)

        task = self._task_from_request(request)
        if not task:
            return Response({"task": "Task obbligatoria."}, status=status.HTTP_400_BAD_REQUEST)

        pool_task = list(contratto.pool_task or [])
        if task in pool_task:
            contratto.pool_task = [pool_task_item for pool_task_item in pool_task if pool_task_item != task]
            contratto.full_clean()
            contratto.save(update_fields=["pool_task"])

        return Response(ContrattoClienteSerializer(contratto).data, status=status.HTTP_200_OK)
