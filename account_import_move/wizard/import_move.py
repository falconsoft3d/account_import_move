#-*- coding: utf-8 -*-

import os
import csv
import tempfile
from odoo.exceptions import UserError
from odoo import fields, models


class ImportAsiento(models.TransientModel):
    _name = "wizard.import.asiento"

    company_id = fields.Many2one(
        'res.company', string='Compañia',
        default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.user.company_id.currency_id)

    file_data = fields.Binary('Archivo', required=True,)
    journal_id = fields.Many2one(
        'account.journal', string='Diario', required=True)
    file_name = fields.Char('File Name')
    ref = fields.Char('Referencia', required=True)
    date = fields.Date(
        string="Fecha", default=fields.Date.today, required=True)

    def import_move_button(self):
        if self.file_name:
            ext = os.path.splitext(self.file_name)

        if ext[-1].upper() != '.CSV':
            raise UserError('Error', 'Formato de archivo no valido!')

        file_path = '{}/file.csv'.format(tempfile.gettempdir())
        data = self.file_data
        f = open(file_path, 'wb')
        f.write(data.decode('base64'))
        f.close()

        move_lines_csv = csv.DictReader(open(file_path), delimiter=',')

        account_obj = self.env['account.account']
        partner_obj = self.env['res.partner']
        analitic_obj = self.env['account.analytic.account']

        count = 1
        move_lines = []
        for line in move_lines_csv:

            val_line = {}
            count += 1
            print count

            credit = float(line['credit'].strip().replace(',', '.'))
            debit = float(line['debit'].strip().replace(',', '.'))

            move_date = line['date'].replace(
                '-', '/') if line['date'].replace('-', '/') else False

            etiqueta = line['description'].replace(
                ';', '') if line['description'].replace(';', '') else self.ref

            print "Etiqueta:" + etiqueta

            val_line = {
                'credit': credit,
                'debit': debit,
                'name': etiqueta,
                'date_maturity': move_date
            }

            # print line

            if line['code']:
                print "Revisando Cuenta Contable: " + line['code']
                print "Insertando [" + str(count) + "] " + line['code']
                account_id = account_obj.search(
                    [('code', '=', line['code'].strip())])

                if account_id:
                    val_line.update({'account_id': account_id.id, })
                else:
                    raise UserError(
                        'No existe información sobre la cuenta contable {0}, ubicada en la \
                                linea {1} del archivo!'.format(
                            line['code'].strip(), count))

            if line['analytic account']:
                print "Revisando Cuenta Analitica: " + line['analytic account']
                analitic_id = analitic_obj.search(
                    [('name', '=', line['analytic account'].strip())])
                if analitic_id:
                    val_line.update({'analytic_account_id': analitic_id.id})
                else:
                    raise UserError(
                        'No existe información sobre la cuenta analitica {0}, ubicada en la \
                        linea {1} del archivo!'.format(
                            line['analytic account'].strip(), count))

            if line['partner']:
                print "Revisando Parner: " + line['partner']
                partner_id = partner_obj.search(
                    [('name', '=', line['partner'].strip())])
                if partner_id:
                    val_line.update({'partner_id': partner_id.id})
                else:
                    raise UserError(
                        'No existe información del partner {0}, ubicado en la \
                        linea {1} del archivo!'.format(
                            line['partner'].strip(), count))

            move_lines.append((0, 0, val_line))

        move_vals = {
            'ref': self.ref,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'line_ids': move_lines
        }
        print "Creando para Insertar"
        # print move_vals
        self.env['account.move'].create(move_vals)
        print "Finalizado"
        return {'type': 'ir.actions.act_window_close'}
