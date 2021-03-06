# Copyright (c) 2015 Presslabs SRL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from django.test import TestCase

from silver.models import DocumentEntry, Invoice, Proforma
from silver.tests.factories import ProformaFactory, DocumentEntryFactory


class TestProforma(TestCase):
    def test_pay_proforma_related_invoice_state_change_to_paid(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.create_invoice()

        proforma.pay()
        proforma.save()

        assert proforma.invoice.state == Invoice.STATES.PAID
        assert proforma.state == Invoice.STATES.PAID

    def test_clone_proforma_into_draft(self):
        proforma = ProformaFactory.create()
        proforma.issue()
        proforma.pay()
        proforma.save()

        entries = DocumentEntryFactory.create_batch(3)
        proforma.proforma_entries.add(*entries)

        clone = proforma.clone_into_draft()

        assert clone.state == Proforma.STATES.DRAFT
        assert clone.paid_date is None
        assert clone.issue_date is None
        assert clone.invoice is None
        assert (clone.series != proforma.series or
                clone.number != proforma.number)
        assert clone.sales_tax_percent == proforma.sales_tax_percent
        assert clone.sales_tax_name == proforma.sales_tax_name

        assert not clone.archived_customer
        assert not clone.archived_provider
        assert clone.customer == proforma.customer
        assert clone.provider == proforma.provider

        assert clone.currency == proforma.currency
        assert clone._last_state == clone.state
        assert clone.pk != proforma.pk
        assert clone.id != proforma.id
        assert not clone.pdf

        assert clone.proforma_entries.count() == 3
        assert proforma.proforma_entries.count() == 3

        entry_fields = [entry.name for entry in DocumentEntry._meta.get_fields()]
        for clone_entry, original_entry in zip(clone.proforma_entries.all(),
                                               proforma.proforma_entries.all()):
            for entry in entry_fields:
                if entry not in ('id', 'proforma', 'invoice'):
                    assert getattr(clone_entry, entry) == \
                        getattr(original_entry, entry)

        assert proforma.state == Proforma.STATES.PAID

    def test_cancel_issued_proforma_with_related_invoice(self):
        proforma = ProformaFactory.create()
        proforma.issue()

        if not proforma.invoice:
            proforma.create_invoice()

        proforma.cancel()
        proforma.save()

        assert proforma.state == proforma.invoice.state == Proforma.STATES.CANCELED
