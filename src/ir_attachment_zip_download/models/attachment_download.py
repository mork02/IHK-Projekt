from odoo import _, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _name = "attachment.download"
    _description = "Attachment Download"

    def prepare_attachment(self):
        selected_ids = self.env.context.get("active_ids", [])
        if not selected_ids:
            raise UserError(_("No attachments selected."))

        attachments = (
            self.env["ir.attachment"]
            .browse(selected_ids)
            .filtered(lambda x: x.type == "binary")
        )
        if not attachments:
            raise UserError(_("No binary attachments available for download."))

        return {
            "type": "ir.actions.act_url",
            "url": "/web/attachment/download_zip?ids={}".format(
                ",".join(map(str, attachments.ids))
            ),
            "target": "self",
        }

    def download_attachment(self):
        items = self.filtered(lambda x: x.type == "binary")

        if not items:
            error_message = _(
                """
                No attachments available for download.
                Only binary attachments that have not been downloaded are allowed.
                """
            )
            raise UserError(error_message)

        ids = ",".join(map(str, items.ids))
        if not ids:
            error_message = _("No valid attachments selected for download.")
            raise UserError(error_message)

        return {
            "type": "ir.actions.act_url",
            "url": "/web/attachment/download_zip?ids=%s" % ids,
            "target": "self",
        }

    def _get_downloadable_attachments(self):
        selected_ids = self.env.context.get("active_ids", [])
        return self.env["ir.attachment"].browse(selected_ids)

    def _get_filename(self):
        self.ensure_one()

        base_name = self.name
        extension = ""
        if "." in base_name:
            base_name, extension = base_name.rsplit(".", 1)
            extension = "." + extension

        existing_names = self.search(
            [("name", "ilike", base_name), ("id", "!=", self.id)]
        ).mapped("name")
        counter = 1
        new_name = base_name + extension

        while new_name in existing_names:
            new_name = "{} ({}){}".format(base_name, counter, extension)
            counter += 1

        self.name = new_name
