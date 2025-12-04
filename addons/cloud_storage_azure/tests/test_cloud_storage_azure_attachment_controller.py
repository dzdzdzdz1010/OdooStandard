import json
import re
from requests import Response
from unittest.mock import patch

import odoo
from odoo.tools.misc import file_open
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.cloud_storage_azure.tests.test_cloud_storage_azure import TestCloudStorageAzureCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestCloudStorageAttachmentController(HttpCaseWithUserDemo, TestCloudStorageAzureCommon):
    def test_cloud_storage_azure_attachment_upload(self):
        """Test uploading an attachment with azure cloud storage."""
        thread = self.env["res.partner"].create({"name": "Test"})
        self.env["ir.config_parameter"].set_param("cloud_storage_provider", "azure")
        self.authenticate(self.user_demo.login, self.user_demo.login)

        def post(url, **kwargs):
            response = Response()
            if url.startswith("https://login.microsoftonline.com"):
                response.status_code = 200
                response._content = bytes(json.dumps({"access_token": "xxx"}), "utf-8")
            if "blob.core.windows.net" in url:
                response.status_code = 200
                response._content = self.DUMMY_USER_DELEGATION_KEY_XML
            return response

        with patch(
            "odoo.addons.cloud_storage_azure.utils.cloud_storage_azure_utils.requests.post", post
        ):
            with file_open("addons/web/__init__.py") as file:
                res = self.url_open(
                    url="/mail/attachment/upload",
                    data={
                        "csrf_token": odoo.http.Request.csrf_token(self),
                        "is_pending": True,
                        "thread_id": thread.id,
                        "thread_model": thread._name,
                        "cloud_storage": True,
                    },
                    files={"ufile": file},
                )
                res.raise_for_status()
                attachment = self.env["ir.attachment"].search([], order="id desc", limit=1)
                # ignore signature in url
                content = re.sub(
                    r'"url": "https://accountname\.blob\.core\.windows\.net/.*?"',
                    '"url": "[url]"',
                    res.content.decode("utf-8"),
                )
                self.assertEqual(
                    json.loads(content),
                    {
                        "data": {
                            "ir.attachment": [
                                {
                                    "access_token": False,
                                    "checksum": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                                    "create_date": odoo.fields.Datetime.to_string(
                                        attachment.create_date
                                    ),
                                    "id": attachment.id,
                                    "mimetype": "text/x-python",
                                    "name": "__init__.py",
                                    "res_name": False,
<<<<<<< dfcd5e63547c75b8eec60f6937e25e67cbf31455
||||||| f95bcc097fd7e70af8d28a66c010ae9b9490f439
                                    "size": 0,
=======
                                    "res_model": attachment.res_model,
                                    "size": 0,
>>>>>>> ab0dba58afd69bf5e4ed622d4f9cdecca0ac0790
                                    "thread": False,
                                    "voice": False,
                                    "type": "cloud_storage",
                                    "url": "[url]",
                                }
                            ],
                        },
                        "upload_info": {
                            "headers": {"x-ms-blob-type": "BlockBlob"},
                            "method": "PUT",
                            "response_status": 201,
                            "url": "[url]",
                        },
                    },
                )
