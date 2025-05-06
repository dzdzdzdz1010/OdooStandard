from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

class DashboardShareRoute(http.Controller):
    @http.route(['/dashboard/share/<int:share_id>/<token>'], type='http', auth='public')
    def share_portal(self, share_id=None, token=None):
        share = request.env["spreadsheet.dashboard.share"].sudo().browse(share_id).exists()
        if not share:
            raise request.not_found()
        share._check_dashboard_access(token)
        download_url = ""
        if request.env.user.has_group('base.group_allow_export'):
            download_url = f"/dashboard/download/{share.id}/{token}"
        return request.render(
            "spreadsheet.public_spreadsheet_layout",
            {
                "spreadsheet_name": share.dashboard_id.name,
                "share": share,
                "is_frozen": True,
                "session_info": request.env["ir.http"].session_info(),
                "props": {
                    "dataUrl": f"/dashboard/data/{share.id}/{token}",
                    "downloadExcelUrl": download_url,
                    "mode": "dashboard",
                },
            },
        )

    @http.route(["/dashboard/download/<int:share_id>/<token>"],
<<<<<<< 7c8de60b9eb243dcbd41bb439c6a98240f4ecade
                type='http', auth='public', readonly=True)
||||||| c4b1ca0d3948f830b78193df9a4d95c2b68b8a72
                type='http', auth='public')
=======
                type='http', auth='user')
>>>>>>> 9df2f8890384481775a258a1d7c7f09ec613506e
    def download(self, token=None, share_id=None):
        share = request.env["spreadsheet.dashboard.share"].sudo().browse(share_id)
        share._check_dashboard_access(token)
        if not request.env.user.has_group('base.group_allow_export'):
            raise UserError(_("You don't have the rights to export data. Please contact an Administrator."))
        stream = request.env["ir.binary"]._get_stream_from(
            share, "excel_export", filename=share.name
        )
        return stream.get_response()

    @http.route(
        ["/dashboard/data/<int:share_id>/<token>"],
        type="http",
        auth="public",
        methods=["GET"],
        readonly=True,
    )
    def get_shared_dashboard_data(self, share_id, token):
        share = (
            request.env["spreadsheet.dashboard.share"]
            .sudo()
            .browse(share_id)
            .exists()
        )
        if not share:
            raise request.not_found()

        share._check_dashboard_access(token)
        stream = request.env["ir.binary"]._get_stream_from(
            share, "spreadsheet_binary_data"
        )
        return stream.get_response()
