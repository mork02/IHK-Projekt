import base64
import zipfile
from datetime import datetime
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IrAttachmentExport(models.Model):
    _name = "ir.attachment.export"
    _description = "Attachment Export"

    name = fields.Char(string="Export Name", required=False, readonly=True)
    start_date = fields.Date(
        string="Start Date", help="File Creation Date", required=True
    )
    end_date = fields.Date(string="End Date", help="File Creation Date", required=True)

    model_ids = fields.Many2many(comodel_name="ir.model", string="Models")

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment", string="Attachments"
    )

    total_attachment_size = fields.Char(
        string="Total File Size",
        readonly=True,
        compute="_compute_total_attachment_size",
        store=True,
    )

    state = fields.Selection(
        [("draft", "Draft"), ("open", "Open"), ("done", "Done")],
        string="State",
        default="draft",
    )

    model_ids_domain = fields.Char(
        string="Model IDs Domain",
        default=lambda self: str([("transient", "=", False)]),
    )

    @api.onchange("model_ids")
    def _onchange_model_ids(self):
        models_with_files = self._get_models()
        additional_domain = (
            self.model_ids_domain if isinstance(self.model_ids_domain, list) else []
        )
        return {
            "domain": {
                "model_ids": [("model", "in", models_with_files)] + additional_domain
            }
        }

    def _get_excluded_files_domains(self):
        return [
            ("name", "not ilike", ".js"),
            ("name", "not ilike", ".css"),
            ("name", "not ilike", ".json"),
            ("name", "not ilike", ".zip"),
        ]

    def _get_models(self, domain=None):
        if domain is None:
            domain = [
                ("res_id", "!=", False),
                ("res_model", "!=", False),
                ("res_model", "!=", "ir.attachment.export"),
            ]
            domain.extend(self._get_excluded_files_domains())

        attachments = self.env["ir.attachment"].read_group(
            domain,
            ["res_model"],
            ["res_model"],
        )
        return [record["res_model"] for record in attachments if record["res_model"]]

    def _get_domain(self):
        domain = []
        if self.model_ids:
            selected_models = [model.model for model in self.model_ids]
            domain.append(("res_model", "in", selected_models))

        domain.extend(
            [
                ("is_exported", "=", False),
                ("create_date", ">=", self.start_date),
                ("create_date", "<=", self.end_date),
                ("file_size", ">", 0),
                ("res_id", "!=", False),
                ("res_model", "!=", False),
            ]
        )
        domain.extend(self._get_excluded_files_domains())

        return domain

    def action_check_attachments(self):
        self.attachment_ids = self.env["ir.attachment"].search(self._get_domain())

        if not self.attachment_ids:
            error_message = _("No attachments found with the given criteria.")
            raise UserError(error_message)

        for attachment in self.attachment_ids:
            attachment.is_exported = True

        self._generate_name()
        self.state = "open"

    @api.depends("attachment_ids")
    def _compute_total_attachment_size(self):
        for record in self:
            total_size_bytes = sum(
                attachment.file_size or 0 for attachment in record.attachment_ids
            )
            record.total_attachment_size = self._format_size(total_size_bytes)

    @api.model
    def _format_size(self, size_in_bytes):
        if size_in_bytes >= 1024**3:
            return "{:.2f} GB".format(size_in_bytes / 1024**3)
        elif size_in_bytes >= 1024**2:
            return "{:.2f} MB".format(size_in_bytes / 1024**2)
        elif size_in_bytes >= 1024:
            return "{:.2f} KB".format(size_in_bytes / 1024)
        else:
            return "{} bytes".format(size_in_bytes)

    def _create_zip_data(self):
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            name_count = {}
            for attachment in self.attachment_ids:
                file_content = base64.b64decode(attachment.datas)
                original_name = attachment.name or attachment.datas_fname
                base_name, extension = original_name, ""
                if "." in original_name:
                    base_name, extension = original_name.rsplit(".", 1)
                    extension = "." + extension
                if original_name in name_count:
                    name_count[original_name] += 1
                    file_name = "{} ({}){}".format(
                        base_name, name_count[original_name], extension
                    )
                else:
                    name_count[original_name] = 0
                    file_name = original_name

                zipf.writestr(file_name, file_content)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    def pack_zip(self):
        zip_data = self._create_zip_data()
        zip_name = "{}.zip".format(self.name)
        encoded_zip = base64.b64encode(zip_data)
        self.env["ir.attachment"].create(
            {
                "name": zip_name,
                "datas": encoded_zip,
                "datas_fname": zip_name,
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/zip",
            }
        )
        self.state = "done"

    def unlink(self):
        self.attachment_ids.write({"is_exported": False})
        return super(IrAttachmentExport, self).unlink()

    def _generate_name(self):
        if not self.name:
            self.name = _("File Export ") + str(
                datetime.today().strftime("%d.%m.%Y - %H:%M")
            )
