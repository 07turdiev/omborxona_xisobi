from rest_framework import viewsets

from apps.core.permissions import IsAdmin
from apps.expenses.models import Expense
from apps.expenses.serializers import ExpenseSerializer


class ExpenseViewSet(viewsets.ModelViewSet):
    """Xarajatlar — sof foydani hisoblash uchun. Administrator uchun."""

    serializer_class = ExpenseSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Expense.objects.all()
        params = self.request.query_params

        if category := params.get('category'):
            queryset = queryset.filter(category=category)

        if date_from := params.get('date_from'):
            queryset = queryset.filter(date__gte=date_from)

        if date_to := params.get('date_to'):
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
