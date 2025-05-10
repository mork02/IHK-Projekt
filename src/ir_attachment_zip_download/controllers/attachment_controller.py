import base64
import zipfile
from datetime import datetime
from io import BytesIO

from odoo import _, http
from odoo.http import content_disposition, request


class AttachmentDownloadController(http.Controller):
    @http.route("/web/attachment/download_zip", type="http", auth="user")
    def download_zip(self, ids=None, **kwargs):
        if not ids:
            return request.not_found()

        attachment_ids = map(int, ids.split(","))
        attachments = (
            request.env["ir.attachment"]
            .browse(attachment_ids)
            .filtered(lambda x: x.type == "binary")
        )

        if not attachments:
            return request.not_found()

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for attachment in attachments:
                try:
                    if attachment.check("read"):
                        file_name = attachment.name
                        base_name = file_name
                        extension = ""
                        if "." in file_name:
                            base_name, extension = file_name.rsplit(".", 1)
                            extension = "." + extension

                        existing_names = [info.filename for info in zip_file.filelist]
                        counter = 1
                        new_name = file_name

                        while new_name in existing_names:
                            new_name = "{} ({}){}".format(base_name, counter, extension)
                            counter += 1

                        if attachment.mimetype in ["text/csv", "text/plain"]:
                            file_data = base64.b64decode(attachment.datas).decode(
                                "utf-8"
                            )
                        else:
                            file_data = base64.b64decode(attachment.datas)

                        zip_file.writestr(new_name, file_data)
                except Exception:
                    continue

        zip_buffer.seek(0)

        current_time = datetime.now()
        filename = _("Attachments ") + current_time.strftime("%d.%m.%Y %H:%M") + ".zip"

        headers = [
            ("Content-Type", "application/zip"),
            ("Content-Disposition", content_disposition(filename)),
        ]
        return request.make_response(zip_buffer.getvalue(), headers=headers)
