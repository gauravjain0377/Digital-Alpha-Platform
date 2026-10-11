import re
from decimal import Decimal
from reconciliation.models import LineItem, TransactionMatch


def normalize_reference(text):
    if not text:
        return ''
    return re.sub(r'[^A-Z0-9]', '', text.upper())


def normalize_name(name):
    if not name:
        return ''
    text_clean = re.sub(r'[^A-Z0-9]+', ' ', name.upper()).strip()
    words = text_clean.split()
    if words and words[-1] in ('LLC', 'LP', 'LTD', 'INC'):
        words.pop()
    return ' '.join(words)


def is_name_in_description(investor_name, description):
    norm_name = normalize_name(investor_name)
    if not norm_name:
        return False
    clean_desc = re.sub(r'[^A-Z0-9]+', ' ', description.upper()).strip()
    pattern = r'\b' + re.escape(norm_name) + r'\b'
    return bool(re.search(pattern, clean_desc))


def match_credit_transaction(transaction):
    eligible = []
    items = LineItem.objects.filter(
        capital_call__organization=transaction.organization,
        capital_call__call_date__lte=transaction.date
    ).select_related('investor_entity', 'capital_call')

    for item in items:
        if item.amount_remaining > Decimal('0.00'):
            eligible.append(item)

    norm_desc = normalize_reference(transaction.description)
    norm_bank_ref = normalize_reference(transaction.bank_reference)

    ref_matches = []
    for item in eligible:
        norm_ref = normalize_reference(item.reference)
        if norm_ref and (norm_ref in norm_desc or norm_ref in norm_bank_ref):
            ref_matches.append(item)

    if ref_matches:
        if len(ref_matches) == 1:
            item = ref_matches[0]
            if transaction.amount <= item.amount_remaining:
                reason = f"Reference {item.reference} found; amount equals or is within remaining {item.amount_remaining}"
                TransactionMatch.objects.create(transaction=transaction, line_item=item, status='proposed', reason=reason)
                transaction.status = 'suggested'
                transaction.review_reason = reason
            else:
                transaction.status = 'needs_review'
                transaction.review_reason = f"Reference {item.reference} found but amount {transaction.amount} exceeds remaining {item.amount_remaining} (overpayment)"
        else:
            transaction.status = 'needs_review'
            transaction.review_reason = f"Multiple matching references found ({', '.join(i.reference for i in ref_matches)})"
            for item in ref_matches:
                reason = f"Reference {item.reference} found"
                TransactionMatch.objects.create(transaction=transaction, line_item=item, status='proposed', reason=reason)
        transaction.save()
        return

    name_matches = []
    for item in eligible:
        if item.amount_remaining == transaction.amount and is_name_in_description(item.investor_entity.name, transaction.description):
            name_matches.append(item)

    if len(name_matches) == 1:
        item = name_matches[0]
        reason = f"Investor name found; amount equals remaining {item.amount_remaining}"
        TransactionMatch.objects.create(transaction=transaction, line_item=item, status='proposed', reason=reason)
        transaction.status = 'suggested'
        transaction.review_reason = reason
    elif len(name_matches) > 1:
        transaction.status = 'needs_review'
        transaction.review_reason = f"Multiple candidates match investor name and amount ({', '.join(i.reference for i in name_matches)})"
        for item in name_matches:
            reason = f"Investor name found; amount equals remaining {item.amount_remaining}"
            TransactionMatch.objects.create(transaction=transaction, line_item=item, status='proposed', reason=reason)
    else:
        transaction.status = 'needs_review'
        transaction.review_reason = "No matching reference or investor name found for amount"

    transaction.save()
