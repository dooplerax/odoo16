from odoo import api, exceptions, fields, models, _
from collections import defaultdict
from datetime import timedelta
from operator import itemgetter

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet, groupby
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Eliminar restriccion para eliminar asientos contables
    # @api.ondelete(at_uninstall=False)
    # def _unlink_except_posted(self):
    #     # Prevent deleting lines on posted entries
    #     if not self._context.get('force_delete') and any(m.state == 'posted' for m in self.move_id):
    #         # raise UserError(_('You cannot delete an item linked to a posted entry.'))
    #         print("delete")