from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from reconciliation.models import Organization, InvestorEntity, CapitalCall, LineItem


class Command(BaseCommand):
    help = 'Seed demo data for organizations, capital calls, and line items'

    def handle(self, *args, **options):
        orgs_data = [
            {'slug': 'northwind', 'name': 'Northwind Ventures'},
            {'slug': 'bluebird', 'name': 'Bluebird Capital'},
        ]
        org_map = {}
        for item in orgs_data:
            org, _ = Organization.objects.get_or_create(
                slug=item['slug'],
                defaults={'name': item['name']}
            )
            org_map[item['slug']] = org

        calls_data = [
            {'org': 'northwind', 'number': 1, 'call_date': date(2026, 3, 25), 'due_date': date(2026, 4, 10)},
            {'org': 'northwind', 'number': 2, 'call_date': date(2026, 4, 1), 'due_date': date(2026, 4, 20)},
            {'org': 'bluebird', 'number': 1, 'call_date': date(2026, 4, 1), 'due_date': date(2026, 4, 15)},
        ]
        call_map = {}
        for item in calls_data:
            org = org_map[item['org']]
            cc, _ = CapitalCall.objects.get_or_create(
                organization=org,
                call_number=item['number'],
                defaults={'call_date': item['call_date'], 'due_date': item['due_date']}
            )
            call_map[(item['org'], item['number'])] = cc

        line_items_data = [
            {'org': 'northwind', 'call': 1, 'investor': 'Haller Capital LLC', 'ref': 'CC-1001', 'amount': '27500.00'},
            {'org': 'northwind', 'call': 1, 'investor': 'Rahul Shah Trust', 'ref': 'CC-1002', 'amount': '25000.00'},
            {'org': 'northwind', 'call': 1, 'investor': 'Patel Family Trust', 'ref': 'CC-1003', 'amount': '12500.00'},
            {'org': 'northwind', 'call': 1, 'investor': 'Meridian Partners LP', 'ref': 'CC-1004', 'amount': '15000.00'},
            {'org': 'northwind', 'call': 1, 'investor': 'Oakridge Holdings LLC', 'ref': 'CC-1005', 'amount': '15000.00'},
            {'org': 'northwind', 'call': 2, 'investor': 'Oakridge Holdings LLC', 'ref': 'CC-1006', 'amount': '15000.00'},
            {'org': 'bluebird', 'call': 1, 'investor': 'Cedar Grove Fund LP', 'ref': 'CC-2001', 'amount': '40000.00'},
        ]

        for item in line_items_data:
            org = org_map[item['org']]
            investor, _ = InvestorEntity.objects.get_or_create(
                organization=org,
                name=item['investor']
            )
            cc = call_map[(item['org'], item['call'])]
            LineItem.objects.update_or_create(
                capital_call=cc,
                reference=item['ref'],
                defaults={
                    'investor_entity': investor,
                    'amount_called': Decimal(item['amount']),
                    'amount_funded': Decimal('0.00'),
                    'status': 'open',
                }
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded demo data.'))
