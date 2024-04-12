from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class ContactCleanup(models.Model):
    _name = 'contact.cleanup'

    # This function finds and deletes 'res.partner' records that have an empty name and are marked as inactive.
    @api.model
    def cleanup_contacts(self):
        contacts_to_delete = self.env['res.partner'].search([('name', '=', False),('active', '=', False)])
        num_deleted = len(contacts_to_delete)
        contacts_to_delete.unlink()
        _logger.info("Deleted %s contacts with empty name", num_deleted)

class IrCron(models.Model):
    _inherit = 'res.partner'

    # This feature acts as a handler for scheduled contact cleaning.
    @api.model
    def scheduler_cleanup_contacts(self):
        self.env['contact.cleanup'].cleanup_contacts()