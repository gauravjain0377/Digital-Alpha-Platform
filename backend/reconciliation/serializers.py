from rest_framework import serializers
from .models import Organization, LineItem, BankTransaction, TransactionMatch


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'slug']


class LineItemSerializer(serializers.ModelSerializer):
    investor_name = serializers.CharField(source='investor_entity.name', read_only=True)
    capital_call_number = serializers.IntegerField(source='capital_call.call_number', read_only=True)
    amount_remaining = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = LineItem
        fields = [
            'id',
            'reference',
            'investor_name',
            'capital_call_number',
            'amount_called',
            'amount_funded',
            'amount_remaining',
            'status',
        ]


class TransactionMatchSerializer(serializers.ModelSerializer):
    line_item_reference = serializers.CharField(source='line_item.reference', read_only=True)
    investor_name = serializers.CharField(source='line_item.investor_entity.name', read_only=True)
    line_item_remaining = serializers.DecimalField(source='line_item.amount_remaining', max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = TransactionMatch
        fields = [
            'id',
            'line_item',
            'line_item_reference',
            'investor_name',
            'line_item_remaining',
            'status',
            'reason',
        ]


class BankTransactionSerializer(serializers.ModelSerializer):
    matches = TransactionMatchSerializer(many=True, read_only=True)

    class Meta:
        model = BankTransaction
        fields = [
            'id',
            'date',
            'description',
            'amount',
            'type',
            'bank_reference',
            'status',
            'review_reason',
            'matches',
        ]
