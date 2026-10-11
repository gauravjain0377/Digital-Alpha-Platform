from django.urls import path
from .views import (
    OrganizationListView,
    ImportCSVView,
    TransactionListView,
    LineItemListView,
    ApproveMatchView,
    RejectMatchView,
    IgnoreTransactionView,
)

urlpatterns = [
    path('organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('import/', ImportCSVView.as_view(), name='import-csv'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('line-items/', LineItemListView.as_view(), name='line-item-list'),
    path('matches/<int:pk>/approve/', ApproveMatchView.as_view(), name='approve-match'),
    path('matches/<int:pk>/reject/', RejectMatchView.as_view(), name='reject-match'),
    path('transactions/<int:pk>/ignore/', IgnoreTransactionView.as_view(), name='ignore-transaction'),
]
