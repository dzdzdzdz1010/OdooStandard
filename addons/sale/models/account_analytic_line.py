from odoo import api, fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    reinvoice_id = fields.Many2one(
        'account.move',
        string="Invoice",
        readonly=True,
        copy=False,
        help="Invoice created from related SO line",
        index='btree_not_null',
    )
    so_line = fields.Many2one(
        'sale.order.line',
        string='Sales Order Item',
        index='btree_not_null',
    )
    order_id = fields.Many2one('sale.order', string="Customer Order", index=True)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('from_services_and_material'):
            for vals in vals_list:
                if vals.get('order_id', False):
                    plan_id = self.env.ref('sale.analytic_plan_sale_orders', raise_if_not_found=False)

                    # If user deleted plan then fallback on project plan
                    if not plan_id:
                        plan_id, _ = self.env['account.analytic.plan']._get_all_plans()

                    order_id = self.env['sale.order'].browse(vals['order_id'])
                    vals[plan_id._column_name()] = (
                        order_id._get_or_create_analytic_account(plan_id).id
                    )

            lines = super().create(vals_list)
            lines._sync_so_lines()
        else:
            lines = super().create(vals_list)

        return lines

    def write(self, vals):
        if self.env.context.get('from_services_and_material'):
            if 'order_id' in vals or 'product_id' in vals:
                # Reset delivered quantity on old sale order line if order or product is changed
                self._sync_so_quantity(0, self.so_line, True)

            if 'unit_amount' in vals:
                # sync delivered quantity if quantity is changed
                self._sync_so_quantity(vals['unit_amount'], self.so_line, True)

            res = super().write(vals)

            if 'order_id' in vals or 'product_id' in vals:
                # create/update sale order line for new order or product
                self._sync_so_lines()

        else:
            res = super().write(vals)

        return res

    @api.ondelete(at_uninstall=False)
    def _unsync_so_lines(self):
        """ Reverse the synchronization of delivered quantities on related sale order lines
        when analytic lines are deleted.

        This method decreases the delivered quantity of the linked sale order line by
        the amount contributed by the analytic line being removed.

        Only sale order lines with a manual delivery method are adjusted, as other lines
        may originate from timesheets or expenses and should not be altered by analytic
        line deletion.
        """
        for line in self:
            if line.so_line.qty_delivered_method == 'manual':
                line._sync_so_quantity(-line.unit_amount, line.so_line)

    def _sync_so_lines(self):
        """ Ensure that a corresponding sale order line exists and is synchronized
        with the current analytic line.

        Depending on the product's expense policy:

        - For 'cost' policy:
          A new sale order line with product's cost is always created with delivered quantity
          equal to the analytic line's unit amount.

        - For 'sales_price' policy:
          The method first attempts to find an existing sale order line
          matching the product. If found, its delivered quantity is updated.
          Otherwise, a new sale order line is created with product's sales price.

        The analytic line is then linked to the resulting sale order line.
        """
        for line in self:
            if not line.order_id or not line.product_id:
                continue

            policy = line.product_id.expense_policy

            if policy == 'cost':
                so_line = self._create_so_line(
                    qty_delivered=line.unit_amount,
                    description=line.name,
                    policy=policy,
                )
                line.so_line = so_line

            elif policy == 'sales_price':
                so_line = line._get_existing_so_line()

                if so_line:
                    line._sync_so_quantity(line.unit_amount, so_line)
                else:
                    so_line = self._create_so_line(
                        qty_delivered=line.unit_amount,
                        description=line.name,
                        policy=policy,
                    )

                line.so_line = so_line

    def _get_existing_so_line(self):
        """ Retrieve an existing sale order line from the related order that
        matches the product of the current analytic line and has manual quantity delivered method.
        """
        return self.order_id.order_line.filtered(
            lambda line: line.product_id == self.product_id
            and line.qty_delivered_method == 'manual',
        )[:1]

    def _create_so_line(self, qty_delivered, description, policy):
        """ Create a new sale order line corresponding to this analytic line.

        The created line is initialized with delivered quantity based on the
        analytic line amount, unit price derived from the product's expense
        policy, and an optional custom description.

        :param float qty_delivered: Quantity to set as delivered on the new sale order line.
        :param str description: Description to assign to the sale order line.
        :param str policy: Expense policy of the product ('cost' or 'sales_price').

        :rtype: sale.order.line
        :return: The newly created sale order line record.
        """
        values = {
            'order_id': self.order_id.id,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_id.id,
            'product_uom_qty': 0,
            'qty_delivered': qty_delivered,
        }

        if description:
            values['name'] = description

        if policy == 'cost':
            values['price_unit'] = self.product_id.standard_price
        elif policy == 'sales_price':
            values['price_unit'] = self.product_id.list_price

        return self.env['sale.order.line'].create(values)

    def _sync_so_quantity(self, quantity, so_line, from_write=False):
        """ Adjust the delivered quantity on a linked sale order line based on
        changes to the analytic line.

        When called from a write operation, the method computes the difference
        between the provided quantity and the current unit amount in order to
        apply only the incremental change.

        :param float quantity: New quantity value to synchronize with the sale order line.
        :param sale.order.line so_line: Sale order line whose delivered quantity must be updated.
        :param bool from_write: Indicates whether the call originates from a write operation.

        :rtype: None
        """
        if not so_line:
            return
        if from_write:
            quantity_diff = quantity - self.unit_amount
        else:
            quantity_diff = quantity
        so_line.qty_delivered += quantity_diff
