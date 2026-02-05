# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PortalProjectSharingController(http.Controller):
    def _get_applicant_sharing_company(self):
        return request.env.company

    def _prepare_applicant_sharing_session_info(self):
        session_info = request.env['ir.http'].session_info()
        user_context = dict(request.env.context) if request.session.uid else {}
        if request.env.lang:
            lang = request.env.lang
            session_info['user_context']['lang'] = lang
            user_context['lang'] = lang

        applicant_company = self._get_applicant_sharing_company()

        session_info.update(
            action_name='portal_project_sharing_demo.hr_applicant_portal_kanban_action',
            user_companies={
                'current_company': applicant_company.id,
                'allowed_companies': {
                    applicant_company.id: {
                        'id': applicant_company.id,
                        'name': applicant_company.name,
                    },
                },
            },
            currencies=request.env['res.currency'].get_all_currencies(),
        )
        return session_info

    @http.route([
        '/my/applicants/embedded_kanban',
        '/my/applicants/embedded_kanban/<path:subpath>',
    ], type='http', auth='user', methods=['GET'])
    def render_embedded_applicant_kanban(self, subpath=None):
        if not request.env['hr.applicant'].check_access_rights('read', raise_exception=False):
            return request.not_found()
        return request.render(
            'portal_project_sharing_demo.portal_project_sharing_portal',
            {'session_info': self._prepare_applicant_sharing_session_info()},
        )
