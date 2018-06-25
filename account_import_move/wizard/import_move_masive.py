#-*- coding: utf-8 -*-

import os
import csv
import tempfile
from odoo.exceptions import UserError
from odoo import fields, models
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class ImportAsientoMasive(models.TransientModel):
    _name = "wizard.import.asiento.masive"

    file_data = fields.Binary('Archivo', required=True,)
    file_name = fields.Char('File Name')
    delimiter = fields.Selection(
        [(';', 'Punto y Coma'),
         (',', 'Coma')],
        'Delimitador', default=';',required=True)
    
    def import_move_button(self):
        if self.file_name:
            ext = os.path.splitext(self.file_name)

        if ext[-1].upper() != '.CSV':
            raise UserError('Error', 'Formato de archivo no valido!')

        file_path = '{}/masive_moves.csv'.format(tempfile.gettempdir())
        data = self.file_data
        f = open(file_path, 'wb')
        f.write(data.decode('base64'))
        f.close()

        move_lines_csv = csv.DictReader(open(file_path), delimiter=str(self.delimiter))

        account_obj = self.env['account.account']
        partner_obj = self.env['res.partner']
        analitic_obj = self.env['account.analytic.account']
        journal_obj = self.env['account.journal']
        account_move_obj = self.env['account.move']

        count = 1
        moves = []
        move_lines = []
        numero = ''
        for row in move_lines_csv:
            count += 1
            #   CREACION Y VALIDACION DE LA CABECERA DEL ASIENTO
            if row.get(''):
                continue
            #   Validacion de la referencia
            if row.get('numero').strip():
                pass
            else:
                raise UserError(
                    'El número es información requerida. Verificar en la \
                         linea {0} del archivo!'.format(count))

            if row.get('ref').strip():
                pass
            else:
                raise UserError(
                    'La referencia es requerida. Verificar en la \
                         linea {0} del archivo!'.format(count))

            #   Validacion del diario
            if row.get('journal_id').strip():
                journal_id = journal_obj.search(
                    [('name', '=', row.get('journal_id').strip())])

                if journal_id:
                    pass
                else:
                    raise UserError(
                        'No existe información el diario {0}, ubicada en la \
                                linea {1} del archivo!'.format(
                            row.get('journal_id').strip(), count))
            else:
                raise UserError(
                    'la información del diario es requerida. Verificar en la \
                         linea {0} del archivo!'.format(count))

            #   Validacion de la fecha del asiento
            if row.get('date_move').strip():
                pass
            else:
                raise UserError(
                    'La fecha del asiento es requerida. Verificar en la \
                         linea {0} del archivo!'.format(count))
            val_line = {}
            credit = float(row.get('credit').strip().replace(',', '.'))
            debit = float(row.get('debit').strip().replace(',', '.'))

            val_line = {
                'numero': row['numero'],
                'date_move': row['date_move'],
                'move_journal_id': journal_id.id,
                'ref': row['ref'],
                'credit': credit,
                'debit': debit,
                'name': row.get('description') if row.get('description') else row.get('ref'),
                'date_maturity': row['date'] if row.get('date') else False
            }

            if row.get('code').strip():

                account_id = account_obj.search(
                    [('code', '=', row.get('code').strip())])

                if account_id:
                    val_line.update({'account_id': account_id.id, })
                else:
                    raise UserError(
                        'No existe información sobre la cuenta contable {0}, ubicada en la \
                                linea {1} del archivo!'.format(
                            row.get('code').strip(), count))
            else:
                raise UserError(
                    'La cuenta contable es requerida. Verificar en la \
                         linea {0} del archivo!'.format(count))

            #   Validacion del partner de la linea
            if row.get('partner').strip():

                partner_id = partner_obj.search(
                    [('name', '=', row.get('partner').strip())])

                if partner_id:
                    val_line.update({'partner_id': partner_id.id})
                else:
                    raise UserError(
                        'No existe información del partner {0}, ubicado en la \
                        linea {1} del archivo!'.format(
                            row['partner'].strip(), count))

            #   Validacion de la descripcion de la linea
            if row.get('analytic_account').strip():

                analitic_id = analitic_obj.search(
                    [('name', '=', row.get('analytic_account').strip())])
                if analitic_id:
                    val_line.update({'analytic_account_id': analitic_id.id})
                else:
                    raise UserError(
                        'No existe información sobre la cuenta analitica {0}, ubicada en la \
                        linea {1} del archivo!'.format(
                            row['analytic_account'].strip(), count))
            if row['numero'] not in moves:
                moves.append(row['numero'])
            move_lines.append(val_line)
        contador = 0
        for move in moves:
            ml = []
            ref = ''
            journal_id = False
            date_move = ''
            for line in move_lines:
                if line.get('numero',False) and line['numero'] == move:
                    line_to_append = line
                    ref = line_to_append['ref']
                    journal_id = line_to_append['move_journal_id']
                    date_move = line_to_append['date_move']
                    line_to_append.pop('numero')
                    line_to_append.pop('ref')
                    line_to_append.pop('move_journal_id')
                    line_to_append.pop('date_move')
                    ml.append((0,0,line_to_append))
            contador += len(ml)
            obj = account_move_obj.create({
                'ref': ref,
                'date': date_move,
                'journal_id': journal_id,
                'line_ids': ml
            })
            _logger.info('Creado Asiento %s'%obj.ref)
        _logger.info('Finalizada carga, %s'%contador)

        return {'type': 'ir.actions.act_window_close'}
