import base64
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError

class TestAttachmentDownload(TransactionCase):

    def setUp(self):
        super(TestAttachmentDownload, self).setUp()
        self.Attachment = self.env['ir.attachment']

        self.attachment_1 = self.Attachment.create({
            'name': 'test_file_1.txt',
            'type': 'binary',
            'datas': base64.b64encode(b"Sample content for file 1"),
            'mimetype': 'text/plain',
        })

        self.attachment_2 = self.Attachment.create({
            'name': 'test_file_2.csv',
            'type': 'binary',
            'datas': base64.b64encode(b"Sample content for file 2"),
            'mimetype': 'text/csv',
        })

        self.attachment_non_binary = self.Attachment.create({
            'name': 'test_file_3.txt',
            'type': 'url',
            'url': 'http://example.com/test_file_3.txt',
        })

    def test_action_download_attachments_with_attachments(self):
        self.env.context = dict(self.env.context, active_ids=[self.attachment_1.id, self.attachment_2.id])

        result = self.attachment_1.prepare_attachment()
        
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('/web/attachment/download_zip?ids=', result['url'])

    def test_action_download_attachments_no_attachments(self):
        self.env.context = dict(self.env.context, active_ids=[])
        result = self.attachment_1.prepare_attachment()

        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(result['params']['type'], 'warning')
        self.assertEqual(result['params']['title'], 'No attachment!')
        self.assertEqual(result['params']['message'], 'There is no document found to download.')

    def test_action_attachments_download_only_binary(self):
        with self.assertRaises(UserError) as e:
            self.attachment_non_binary.with_context(active_ids=[self.attachment_non_binary.id]).download_attachment()
        self.assertIn('No attachments available for download', str(e.exception))

    def test_compute_zip_file_name(self):
        expected_file_name = 'test_file_1.txt'
        computed_file_name = self.attachment_1._get_filename()
        self.assertEqual(expected_file_name, computed_file_name)
