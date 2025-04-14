# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


class LoyaltyHistory(models.Model):
    _name = 'loyalty.history'
    _description = "History for Loyalty cards and Ewallets"
    _order = 'id desc'

    card_id = fields.Many2one(
        comodel_name='loyalty.card',
        ondelete='cascade',
        readonly=True,
        required=True,
        index=True,
    )
    program_type = fields.Selection(related='card_id.program_type')
    company_id = fields.Many2one(related='card_id.company_id')

    description = fields.Text(required=True)

    issued = fields.Float(readonly=True)
    available_issued_points = fields.Float(string='Available', readonly=True)
    used = fields.Float(
        help="Indicates the number of points claimed on a sale order;"
             " not necessarily deducted from the points issued on the same line.",
        readonly=True,
    )
    active = fields.Boolean(default=True)
    expiration_date = fields.Date(string='Expiration')

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field='order_model', readonly=True)

    def _get_sorted_history_lines(self, lines):
        """
        Sorts loyalty history lines by redemption priority.

        Points are ordered by:
            1. Nearest expiration date (soonest first).
            2. Earlier creation order, if expiration dates are equal.
            3. Points without an expiration date are placed last.
        """
        return lines.sorted(
            key=lambda line: (
                line.expiration_date is False,
                line.expiration_date,
                line.id,
            ),
        )

    def _get_order_portal_url(self):
        self.ensure_one()
        return False

    def _get_order_description(self):
        self.ensure_one()
        return self.env[self.order_model].browse(self.order_id).display_name

    @api.model_create_multi
    def create(self, vals_list):
        today = fields.Date.today()
        for vals in vals_list:
            # The history line is archived immediately as it has no redeemable points.
            if vals.get('available_issued_points') == 0:
                vals['active'] = False
                continue
            card = self.env['loyalty.card'].browse(vals.get('card_id'))
            if expire_after := card.program_id.expire_after:
                vals['expiration_date'] = today + timedelta(days=expire_after)
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        today = fields.Date.today()
        if 'expiration_date' in vals:
            for line in self:
                if line.expiration_date < today:
                    line.card_id.points -= line.available_issued_points
                    line.available_issued_points = 0
                    line.active = False
        return result

    def compensate_existing_debts(self, compensation_records):
        """
        When new points are issued,
        settle any existing negative (debt) mappings for same card.
        """
        history_lines_mapping = self.env['loyalty.history.link'].sudo()

        for coupon in compensation_records:
            card_id = coupon.get('card_id')
            new_issuer_line_id = coupon.get('redeemer_history_line_id')

            new_issuer_line = self.browse(new_issuer_line_id)

            # Debt history lines that have negative points which needs to be compensated.
            debts = history_lines_mapping.search([
                ('issuer_line_id', '=', False),
                ('points', '<', 0),
                ('redeemer_line_id.card_id', '=', card_id),
            ])

            for debt in debts:
                debt_points = abs(debt.points)
                compensate = min(debt_points, new_issuer_line.available_issued_points)

                history_lines_mapping.create({
                    'issuer_line_id': new_issuer_line.id,
                    'redeemer_line_id': debt.redeemer_line_id.id,
                    'points': compensate,
                })

                debt.points += compensate
                if debt.points == 0:
                    debt.unlink()

                new_issuer_line.available_issued_points -= compensate
                if new_issuer_line.available_issued_points <= 0:
                    new_issuer_line.active = False
                    break

    def redeem_loyalty_points(self, redemption_records):
        """
        Attempts to allocate available issuer history lines to fulfill the redeemer's request.
        If available points are insufficient, a debt entry is created with no issuer line linked
        """
        history_lines_mapping = self.env['loyalty.history.link'].sudo()

        for coupon in redemption_records:
            card_id = coupon.get('card_id')
            points_to_redeem = coupon.get('points_to_redeem')
            redeemer_line_id = coupon.get('redeemer_history_line_id')
            exclude_issuer_ids = coupon.get('exclude_issuer_ids') or []

            # find redeemable issuer lines and sort them to use them in order
            redeemable_history_lines = self.search([('card_id', '=', card_id)])
            sorted_lines = self._get_sorted_history_lines(redeemable_history_lines)

            for issuer_line in sorted_lines:
                if issuer_line.id in exclude_issuer_ids:
                    continue

                redeemable_points = min(issuer_line.available_issued_points, points_to_redeem)
                issuer_line.available_issued_points -= redeemable_points
                if issuer_line.available_issued_points == 0:
                    issuer_line.active = False

                # create mapping of issuer -> redeemer further reference
                mapping_vals = {
                    'issuer_line_id': issuer_line.id,
                    'redeemer_line_id': redeemer_line_id,
                    'points': redeemable_points,
                }
                history_lines_mapping.create(mapping_vals)

                points_to_redeem -= redeemable_points
                if points_to_redeem <= 0:
                    break

            # If not fully covered, create debt mapping only for an active redeemer
            if points_to_redeem > 0 and redeemer_line_id:
                history_lines_mapping.create({
                    'issuer_line_id': False,
                    'redeemer_line_id': redeemer_line_id,
                    'points': -points_to_redeem,
                })

    @api.model
    def _cron_expire_loyalty_points(self):
        """
        Expire and archive history lines and recompute total card balance.
        """
        today = fields.Date.today()
        expired_lines = self.with_context(active_test=False).search([
            ('expiration_date', '<', today),
        ])

        if not expired_lines:
            return

        for line in expired_lines:
            line.card_id.points -= line.available_issued_points

        expired_lines.write({
            'available_issued_points': 0,
            'active': False,
        })
