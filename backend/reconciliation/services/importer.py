import csv
import io
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.db import transaction
from reconciliation.models import BankTransaction


class MissingColumnError(Exception):
    pass


REQUIRED_COLUMNS = ['date', 'description', 'amount', 'type', 'reference']


def parse_and_validate_row(row_dict, line_number):
    clean = {k: v.strip() if isinstance(v, str) else '' for k, v in row_dict.items()}

    if not clean.get('description'):
        return None, f"Line {line_number}: Description is required"

    if not clean.get('reference'):
        return None, f"Line {line_number}: Reference is required"

    try:
        tx_date = datetime.strptime(clean['date'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None, f"Line {line_number}: Invalid date format or non-existent calendar date '{clean.get('date')}'"

    tx_type = clean.get('type', '').lower()
    if tx_type not in ('credit', 'debit'):
        return None, f"Line {line_number}: Type must be credit or debit, got '{clean.get('type')}'"

    amount_raw = clean.get('amount', '').replace(',', '')
    try:
        amount = Decimal(amount_raw)
    except (InvalidOperation, TypeError):
        return None, f"Line {line_number}: Invalid amount value '{clean.get('amount')}'"

    if amount == Decimal('0.00'):
        return None, f"Line {line_number}: Amount cannot be zero"

    if tx_type == 'credit' and amount <= Decimal('0.00'):
        return None, f"Line {line_number}: Credit amount must be positive"

    if tx_type == 'debit' and amount >= Decimal('0.00'):
        return None, f"Line {line_number}: Debit amount must be negative"

    return {
        'date': tx_date,
        'description': clean['description'],
        'amount': amount,
        'type': tx_type,
        'bank_reference': clean['reference'],
    }, None


def import_bank_statement_csv(file_obj, organization, matcher_fn=None):
    if hasattr(file_obj, 'read'):
        content = file_obj.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig')
    else:
        content = str(file_obj)

    reader = csv.reader(io.StringIO(content))
    try:
        header = next(reader)
    except StopIteration:
        raise MissingColumnError("CSV file is empty")

    header_clean = [col.strip().lower() for col in header]
    missing = [col for col in REQUIRED_COLUMNS if col not in header_clean]
    if missing:
        raise MissingColumnError(f"Missing required columns: {', '.join(missing)}")

    col_index = {col: header_clean.index(col) for col in REQUIRED_COLUMNS}

    imported_count = 0
    duplicate_count = 0
    errors = []
    seen_references = set()

    line_number = 1
    for row in reader:
        line_number += 1
        if not row or not any(row):
            continue

        row_dict = {}
        for col in REQUIRED_COLUMNS:
            idx = col_index[col]
            row_dict[col] = row[idx] if idx < len(row) else ''

        parsed, error_msg = parse_and_validate_row(row_dict, line_number)
        if error_msg:
            errors.append({'line': line_number, 'message': error_msg})
            continue

        bank_ref = parsed['bank_reference']
        if bank_ref in seen_references:
            duplicate_count += 1
            continue

        if BankTransaction.objects.filter(organization=organization, bank_reference=bank_ref).exists():
            duplicate_count += 1
            seen_references.add(bank_ref)
            continue

        seen_references.add(bank_ref)

        with transaction.atomic():
            if parsed['type'] == 'debit':
                tx = BankTransaction.objects.create(
                    organization=organization,
                    date=parsed['date'],
                    description=parsed['description'],
                    amount=parsed['amount'],
                    type='debit',
                    bank_reference=bank_ref,
                    status='ignored',
                    review_reason='Debit transaction'
                )
            else:
                tx = BankTransaction.objects.create(
                    organization=organization,
                    date=parsed['date'],
                    description=parsed['description'],
                    amount=parsed['amount'],
                    type='credit',
                    bank_reference=bank_ref,
                    status='needs_review',
                    review_reason=''
                )
                if matcher_fn:
                    matcher_fn(tx)

            imported_count += 1

    return {
        'imported_count': imported_count,
        'duplicate_count': duplicate_count,
        'errors': errors,
    }
