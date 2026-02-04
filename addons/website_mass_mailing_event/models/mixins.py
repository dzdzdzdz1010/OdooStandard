# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.json import scriptsafe as json_safe


class WebsiteCover_PropertiesMixin(models.AbstractModel):
    _inherit = 'website.cover_properties.mixin'

    def _get_cover_url(self):
        self.ensure_one()
        properties = json_safe.loads(self.cover_properties)
        img_src = properties.get('background-image', '/web/static/img/placeholder.png')
        if img_src.startswith('url('):
            # remove first four characters and last character of image url
            img_src = img_src[5:-2]
        return img_src
