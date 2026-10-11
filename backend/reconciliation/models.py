from decimal import Decimal
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class InvestorEntity(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='investors')
    name = models.CharField(max_length=200)

    class Meta:
        unique_together = ('organization', 'name')

    def __str__(self):
        return f"{self.name} ({self.organization.slug})"


class CapitalCall(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='capital_calls')
    call_number = models.PositiveIntegerField()
    call_date = models.DateField()
    due_date = models.DateField()

    class Meta:
        unique_together = ('organization', 'call_number')

    def __str__(self):
        return f"{self.organization.slug} #{self.call_number}"


class LineItem(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('partially_funded', 'Partially Funded'),
        ('funded', 'Funded'),
    )

    capital_call = models.ForeignKey(CapitalCall, on_delete=models.CASCADE, related_name='line_items')
    investor_entity = models.ForeignKey(InvestorEntity, on_delete=models.CASCADE, related_name='line_items')
    reference = models.CharField(max_length=50)
    amount_called = models.DecimalField(max_digits=14, decimal_places=2)
    amount_funded = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')

    @property
    def amount_remaining(self):
        return self.amount_called - self.amount_funded

    def update_status(self):
        if self.amount_funded <= Decimal('0.00'):
            self.status = 'open'
        elif self.amount_funded < self.amount_called:
            self.status = 'partially_funded'
        else:
            self.status = 'funded'

    def __str__(self):
        return f"{self.reference} - {self.investor_entity.name}"


class BankTransaction(models.Model):
    STATUS_CHOICES = (
        ('suggested', 'Suggested'),
        ('needs_review', 'Needs Review'),
        ('reconciled', 'Reconciled'),
        ('ignored', 'Ignored'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField()
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    type = models.CharField(max_length=10)
    bank_reference = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='needs_review')
    review_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'bank_reference')
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.bank_reference} - {self.amount}"


class TransactionMatch(models.Model):
    STATUS_CHOICES = (
        ('proposed', 'Proposed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    transaction = models.ForeignKey(BankTransaction, on_delete=models.CASCADE, related_name='matches')
    line_item = models.ForeignKey(LineItem, on_delete=models.CASCADE, related_name='matches')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed')
    reason = models.TextField(blank=True, default='')

    def __str__(self):
        return f"Match {self.transaction.bank_reference} -> {self.line_item.reference} ({self.status})"
