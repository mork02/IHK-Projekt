from odoo.tests.common import TransactionCase
from datetime import date, timedelta
import base64
import zipfile
import io


class TestIrAttachmentExportZip(TransactionCase):
    def setUp(self):
        super().setUp()

        model = self.env['ir.model'].search([('model', '=', 'res.country')], limit=1)

        self.attachment = self.env['ir.attachment'].create({
            'name': 'test.pdf',
            'datas': base64.b64encode(b'Testinhalt').decode('utf-8'),
            'datas_fname': 'test.pdf',
            'res_model': model.model,
            'res_id': 1,
            'mimetype': 'application/txt',
            'file_size': 11,
        })

        self.export = self.env["ir.attachment.export"].create({
            "start_date": date.today() - timedelta(days=1),
            "end_date": date.today() + timedelta(days=1),
            "model_ids": [(6, 0, [model.id])],
        })

    def test_check_export_exists(self):
        """Testet, ob Export erfolgreich erstellt wurde"""
        self.export.action_check_attachments()
        # File
        self.assertIn(self.attachment, self.export.attachment_ids)
        # Size
        self.assertGreaterEqual(len(self.export.attachment_ids), 1)
        # Bool
        self.assertTrue(self.attachment.is_exported)

    def test_state_draft(self):
        """Testet, ob 'state = draft' funktioniert"""
        self.assertEqual(self.export.state, 'draft')
        self.assertFalse(self.export.attachment_ids)

    def test_export_filters_and_assigns_attachments(self):
        """Testet das Filtern und Zuweisen von Attachments"""
        self.export.action_check_attachments()
        self.assertEqual(self.export.state, 'open')
        self.assertIn(self.attachment, self.export.attachment_ids)
        self.assertTrue(self.attachment.is_exported)
        self.assertTrue(self.export.total_attachment_size)

    def test_zip_state_done(self):
        """Testet, ob der Status nach dem ZIP-Packen auf 'done' gesetzt wird"""
        self.export.action_check_attachments()
        self.export.pack_zip()
        self.assertEqual(self.export.state, 'done')

        # ZIP-Datei wurde erstellt
        zip_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'ir.attachment.export'),
            ('res_id', '=', self.export.id),
            ('mimetype', '=', 'application/zip')
        ], limit=1)
        self.assertTrue(zip_attachment)

    def test_zip_contains_attachment(self):
        """Testet, ob das ZIP-Archiv die richtige Datei enthält"""
        self.export.action_check_attachments()
        self.export.pack_zip()

        # ZIP-Datei laden
        zip_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'ir.attachment.export'),
            ('res_id', '=', self.export.id),
            ('mimetype', '=', 'application/zip')
        ], limit=1)

        # Datei aus ZIP auslesen
        zip_data = base64.b64decode(zip_attachment.datas)
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            zip_filenames = zip_file.namelist()
            self.assertIn(self.attachment.datas_fname, zip_filenames)
            extracted_content = zip_file.read(self.attachment.datas_fname)
            self.assertEqual(extracted_content, b'Testinhalt')
