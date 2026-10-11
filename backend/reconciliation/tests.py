import io
from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from reconciliation.models import Organization, InvestorEntity, CapitalCall, LineItem, BankTransaction, TransactionMatch


class ReconciliationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.org_north = Organization.objects.create(name='Northwind Ventures', slug='northwind')
        self.org_blue = Organization.objects.create(name='Bluebird Capital', slug='bluebird')

        self.inv_haller = InvestorEntity.objects.create(organization=self.org_north, name='Haller Capital LLC')
        self.inv_patel = InvestorEntity.objects.create(organization=self.org_north, name='Patel Family Trust')
        self.inv_oak = InvestorEntity.objects.create(organization=self.org_north, name='Oakridge Holdings LLC')
        self.inv_cedar = InvestorEntity.objects.create(organization=self.org_blue, name='Cedar Grove Fund LP')

        self.call_n1 = CapitalCall.objects.create(organization=self.org_north, call_number=1, call_date=date(2026, 3, 25), due_date=date(2026, 4, 10))
        self.call_n2 = CapitalCall.objects.create(organization=self.org_north, call_number=2, call_date=date(2026, 4, 1), due_date=date(2026, 4, 20))
        self.call_b1 = CapitalCall.objects.create(organization=self.org_blue, call_number=1, call_date=date(2026, 4, 1), due_date=date(2026, 4, 15))

        self.li_cc1001 = LineItem.objects.create(capital_call=self.call_n1, investor_entity=self.inv_haller, reference='CC-1001', amount_called=Decimal('27500.00'))
        self.li_cc1003 = LineItem.objects.create(capital_call=self.call_n1, investor_entity=self.inv_patel, reference='CC-1003', amount_called=Decimal('12500.00'))
        self.li_cc1005 = LineItem.objects.create(capital_call=self.call_n1, investor_entity=self.inv_oak, reference='CC-1005', amount_called=Decimal('15000.00'))
        self.li_cc1006 = LineItem.objects.create(capital_call=self.call_n2, investor_entity=self.inv_oak, reference='CC-1006', amount_called=Decimal('15000.00'))
        self.li_cc2001 = LineItem.objects.create(capital_call=self.call_b1, investor_entity=self.inv_cedar, reference='CC-2001', amount_called=Decimal('40000.00'))

    def upload_csv_content(self, csv_str, org_slug='northwind'):
        file_obj = SimpleUploadedFile('test.csv', csv_str.encode('utf-8'), content_type='text/csv')
        headers = {'HTTP_X_ORGANIZATION': org_slug} if org_slug else {}
        return self.client.post('/api/import/', {'file': file_obj}, format='multipart', **headers)

    def test_1_missing_column_rejects_and_saves_nothing(self):
        csv_data = "date,description,amount,type\n2026-04-03,WIRE INCOMING,25000.00,credit\n"
        response = self.upload_csv_content(csv_data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(BankTransaction.objects.count(), 0)

    def test_2_amount_parsing_and_decimal_types(self):
        csv_data = (
            "date,description,amount,type,reference\n"
            "2026-04-03,VALID ROW,\"25,000.00\",credit,REF001\n"
            "2026-04-31,INVALID DATE,1000.00,credit,REF002\n"
            "2026-04-05,NEGATIVE CREDIT,-500.00,credit,REF003\n"
            "2026-04-06,POSITIVE DEBIT,500.00,debit,REF004\n"
        )
        response = self.upload_csv_content(csv_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['imported_count'], 1)
        self.assertEqual(len(response.data['errors']), 3)

        tx = BankTransaction.objects.get(bank_reference='REF001')
        self.assertIsInstance(tx.amount, Decimal)
        self.assertEqual(tx.amount, Decimal('25000.00'))

    def test_3_duplicates_in_file_and_reupload(self):
        csv_data = (
            "date,description,amount,type,reference\n"
            "2026-04-03,ROW 1,1000.00,credit,REF_DUP\n"
            "2026-04-03,ROW 2 DUP,1000.00,credit,REF_DUP\n"
        )
        resp1 = self.upload_csv_content(csv_data)
        self.assertEqual(resp1.data['imported_count'], 1)
        self.assertEqual(resp1.data['duplicate_count'], 1)

        resp2 = self.upload_csv_content(csv_data)
        self.assertEqual(resp2.data['imported_count'], 0)
        self.assertEqual(resp2.data['duplicate_count'], 2)

    def test_4_reference_match_normalized_and_partial_payment(self):
        csv_data = "date,description,amount,type,reference\n2026-04-04,ACH CREDIT HALLER CAPITAL cc1001,20000.00,credit,ACH_PARTIAL\n"
        response = self.upload_csv_content(csv_data)
        self.assertEqual(response.status_code, 200)

        tx = BankTransaction.objects.get(bank_reference='ACH_PARTIAL')
        self.assertEqual(tx.status, 'suggested')
        match = tx.matches.first()
        self.assertIsNotNone(match)
        self.assertEqual(match.line_item, self.li_cc1001)

    def test_5_name_and_amount_match_and_multiple_candidates(self):
        csv_single = "date,description,amount,type,reference\n2026-04-07,WIRE INCOMING PATEL FAMILY TRUST,12500.00,credit,PATEL_REF\n"
        self.upload_csv_content(csv_single)
        tx_single = BankTransaction.objects.get(bank_reference='PATEL_REF')
        self.assertEqual(tx_single.status, 'suggested')
        self.assertEqual(tx_single.matches.first().line_item, self.li_cc1003)

        csv_multi = "date,description,amount,type,reference\n2026-04-11,WIRE INCOMING OAKRIDGE HOLDINGS LLC,15000.00,credit,OAK_REF\n"
        self.upload_csv_content(csv_multi)
        tx_multi = BankTransaction.objects.get(bank_reference='OAK_REF')
        self.assertEqual(tx_multi.status, 'needs_review')
        self.assertEqual(tx_multi.matches.count(), 2)

    def test_6_overpayment_becomes_needs_review_no_match(self):
        csv_data = "date,description,amount,type,reference\n2026-04-15,WIRE INCOMING PATEL FAMILY TRUST CC-1003,13000.00,credit,OVERPAY_REF\n"
        self.upload_csv_content(csv_data)
        tx = BankTransaction.objects.get(bank_reference='OVERPAY_REF')
        self.assertEqual(tx.status, 'needs_review')
        self.assertEqual(tx.matches.count(), 0)

    def test_7_approve_updates_funded_amount_and_prevents_double_funding(self):
        csv_data = "date,description,amount,type,reference\n2026-04-07,WIRE INCOMING PATEL FAMILY TRUST,12500.00,credit,APPROVE_REF\n"
        self.upload_csv_content(csv_data)
        tx = BankTransaction.objects.get(bank_reference='APPROVE_REF')
        match = tx.matches.first()

        resp1 = self.client.post(f'/api/matches/{match.id}/approve/', HTTP_X_ORGANIZATION='northwind')
        self.assertEqual(resp1.status_code, 200)

        self.li_cc1003.refresh_from_db()
        self.assertEqual(self.li_cc1003.amount_funded, Decimal('12500.00'))
        self.assertEqual(self.li_cc1003.status, 'funded')

        tx.refresh_from_db()
        self.assertEqual(tx.status, 'reconciled')

        resp2 = self.client.post(f'/api/matches/{match.id}/approve/', HTTP_X_ORGANIZATION='northwind')
        self.assertEqual(resp2.status_code, 409)
        self.li_cc1003.refresh_from_db()
        self.assertEqual(self.li_cc1003.amount_funded, Decimal('12500.00'))

    def test_8_organization_isolation(self):
        csv_data = "date,description,amount,type,reference\n2026-04-07,WIRE INCOMING PATEL FAMILY TRUST,12500.00,credit,ISOLATION_REF\n"
        self.upload_csv_content(csv_data, org_slug='northwind')
        tx = BankTransaction.objects.get(bank_reference='ISOLATION_REF')
        match = tx.matches.first()

        resp_list = self.client.get('/api/transactions/', HTTP_X_ORGANIZATION='bluebird')
        self.assertEqual(len(resp_list.data), 0)

        resp_approve = self.client.post(f'/api/matches/{match.id}/approve/', HTTP_X_ORGANIZATION='bluebird')
        self.assertEqual(resp_approve.status_code, 404)

        resp_missing = self.client.get('/api/transactions/')
        self.assertEqual(resp_missing.status_code, 400)

        resp_unknown = self.client.get('/api/transactions/', HTTP_X_ORGANIZATION='nonexistent')
        self.assertEqual(resp_unknown.status_code, 404)
