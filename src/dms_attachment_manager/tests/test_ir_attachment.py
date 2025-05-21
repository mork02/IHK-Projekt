from odoo.tests.common import TransactionCase
from datetime import date, timedelta
import base64


class TestIrAttachmentExportIsExported(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env['ir.model'].search([('model', '=', 'res.country')], limit=1)

        self.attachment = self.env['ir.attachment'].create({
            'name': 'flag_test.pdf',
            'datas': base64.b64encode(b'Testflag').decode('utf-8'),
            'datas_fname': 'flag_test.pdf',
            'res_model': model.model,
            'res_id': 1,
            'mimetype': 'application/txt',
            'file_size': 9,
        })

        self.export = self.env["ir.attachment.export"].create({
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today() + timedelta(days=1),
            "model_ids": [(6, 0, [model.id])],
        })

    def test_is_exported_true_after_check(self):
        """Testet, ob 'is_exported' nach Exportprüfung auf True gesetzt wird."""
        self.assertFalse(self.attachment.is_exported)

        self.export.action_check_attachments()
        self.assertTrue(self.attachment.is_exported)

    def test_is_exported_false_after_unlink(self):
        """Testet, ob 'is_exported' zurückgesetzt wird, wenn Export gelöscht wird."""
        self.export.action_check_attachments()
        self.assertTrue(self.attachment.is_exported)

        self.export.unlink()
        self.attachment.invalidate_cache()
        self.assertFalse(self.attachment.is_exported)
