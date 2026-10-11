from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Organization, LineItem, BankTransaction, TransactionMatch
from .serializers import (
    OrganizationSerializer,
    LineItemSerializer,
    BankTransactionSerializer,
    TransactionMatchSerializer,
)
from .services.importer import import_bank_statement_csv, MissingColumnError


def get_scoped_organization(request):
    org_slug = request.headers.get('X-Organization')
    if not org_slug:
        return None, Response({'error': 'X-Organization header is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        org = Organization.objects.get(slug=org_slug)
        return org, None
    except Organization.DoesNotExist:
        return None, Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)


class OrganizationListView(APIView):
    def get(self, request):
        orgs = Organization.objects.all().order_by('name')
        return Response(OrganizationSerializer(orgs, many=True).data)


class ImportCSVView(APIView):
    def post(self, request):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            summary = import_bank_statement_csv(csv_file, org)
            return Response(summary, status=status.HTTP_200_OK)
        except MissingColumnError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to process file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class TransactionListView(APIView):
    def get(self, request):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        transactions = BankTransaction.objects.filter(organization=org).prefetch_related('matches__line_item__investor_entity')
        return Response(BankTransactionSerializer(transactions, many=True).data)


class LineItemListView(APIView):
    def get(self, request):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        line_items = LineItem.objects.filter(capital_call__organization=org).select_related('investor_entity', 'capital_call').order_by('reference')
        return Response(LineItemSerializer(line_items, many=True).data)


class ApproveMatchView(APIView):
    def post(self, request, pk):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        try:
            match = TransactionMatch.objects.select_related('transaction', 'line_item').get(
                pk=pk,
                transaction__organization=org
            )
        except TransactionMatch.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            locked_tx = BankTransaction.objects.select_for_update().get(pk=match.transaction_id)
            locked_item = LineItem.objects.select_for_update().get(pk=match.line_item_id)
            locked_match = TransactionMatch.objects.select_for_update().get(pk=match.id)

            if locked_tx.status == 'reconciled' or locked_match.status == 'approved':
                return Response({'error': 'Transaction or match already reconciled'}, status=status.HTTP_409_CONFLICT)

            if locked_tx.amount > locked_item.amount_remaining:
                return Response(
                    {'error': f'Amount {locked_tx.amount} exceeds line item remaining amount {locked_item.amount_remaining}'},
                    status=status.HTTP_409_CONFLICT
                )

            locked_item.amount_funded += locked_tx.amount
            locked_item.update_status()
            locked_item.save()

            locked_match.status = 'approved'
            locked_match.save()

            TransactionMatch.objects.filter(transaction=locked_tx).exclude(pk=locked_match.pk).update(status='rejected')

            locked_tx.status = 'reconciled'
            locked_tx.save()

        return Response({'message': 'Match approved successfully', 'match': TransactionMatchSerializer(locked_match).data})


class RejectMatchView(APIView):
    def post(self, request, pk):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        try:
            match = TransactionMatch.objects.select_related('transaction').get(
                pk=pk,
                transaction__organization=org
            )
        except TransactionMatch.DoesNotExist:
            return Response({'error': 'Match not found'}, status=status.HTTP_404_NOT_FOUND)

        match.status = 'rejected'
        match.save()

        tx = match.transaction
        if not tx.matches.filter(status='proposed').exists() and tx.status != 'reconciled':
            tx.status = 'needs_review'
            tx.save()

        return Response({'message': 'Match rejected successfully'})


class IgnoreTransactionView(APIView):
    def post(self, request, pk):
        org, err_resp = get_scoped_organization(request)
        if err_resp:
            return err_resp

        try:
            tx = BankTransaction.objects.get(pk=pk, organization=org)
        except BankTransaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        if tx.status == 'reconciled':
            return Response({'error': 'Cannot ignore a reconciled transaction'}, status=status.HTTP_409_CONFLICT)

        tx.status = 'ignored'
        tx.save()
        tx.matches.filter(status='proposed').update(status='rejected')

        return Response({'message': 'Transaction ignored successfully'})
