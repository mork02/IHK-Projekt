from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import base64
from io import BytesIO
import zipfile


class TestIrAttachmentExport(TransactionCase):
    def setUp(self):
        super(TestIrAttachmentExport, self).setUp()
        self.attachment_model = self.env["ir.attachment"]
        self.export_model = self.env["ir.attachment.export"]

        self.attachment1 = self.attachment_model.create({
            "name": "Test File 1.txt",
            "datas": base64.b64encode(b"Test Content 1"),
            "file_size": len(b"Test Content 1"),
            "res_model": "res.partner",
            "res_id": 1,
        })
        self.attachment2 = self.attachment_model.create({
            "name": "Test File 2.csv",
            "datas": base64.b64encode(b"Test Content 2"),
            "file_size": len(b"Test Content 2"),
            "res_model": "res.partner",
            "res_id": 2,
        })

        self.export_record = self.export_model.create({
            "start_date": (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d'),
            "end_date": datetime.today().strftime('%Y-%m-%d'),
        })

    def test_action_check_attachments(self):
        self.export_record.action_check_attachments()

        self.assertIn(self.attachment1.id, self.export_record.attachment_ids.ids)
        self.assertIn(self.attachment2.id, self.export_record.attachment_ids.ids)

        self.assertEqual(self.export_record.state, "open", "State should be 'open' after checking attachments.")

    def test_compute_total_attachment_size(self):
        self.export_record.attachment_ids = [(6, 0, [self.attachment1.id, self.attachment2.id])]
        self.export_record._compute_total_attachment_size()

        expected_size = len(b"Test Content 1") + len(b"Test Content 2")
        self.assertEqual(
            self.export_record.total_attachment_size,
            self.export_record._format_size(expected_size),
            "Total attachment size computation is incorrect.",
        )

    def test_pack_zip(self):
        self.export_record.attachment_ids = [(6, 0, [self.attachment1.id, self.attachment2.id])]
        self.export_record.pack_zip()

        self.assertTrue(self.export_record.zip_file, "ZIP file should be created.")

        zip_data = base64.b64decode(self.export_record.zip_file)
        with zipfile.ZipFile(BytesIO(zip_data), "r") as zipf:
            file_names = zipf.namelist()
            self.assertIn("Test File 1.txt", file_names, "Test File 1 is missing in the ZIP.")
            self.assertIn("Test File 2.csv", file_names, "Test File 2 is missing in the ZIP.")

    def test_no_attachments_found(self):
        empty_export = self.export_model.create({
            "start_date": (datetime.today() - timedelta(days=10)).strftime('%Y-%m-%d'),
            "end_date": (datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d'),
        })

        with self.assertRaises(UserError, msg="No UserError raised when no attachments are found."):
            empty_export.action_check_attachments()

    def test_state_transitions(self):
        self.assertEqual(self.export_record.state, "draft", "Initial state should be 'draft'.")

        self.export_record.action_check_attachments()
        self.assertEqual(self.export_record.state, "open", "State should transition to 'open' after checking attachments.")

        self.export_record.pack_zip()
        self.assertEqual(self.export_record.state, "done", "State should transition to 'done' after packing ZIP.")
