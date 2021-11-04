from datetime import timedelta

from odoo import fields, models, api, exceptions, _, SUPERUSER_ID


class HrRfidCommands(models.Model):
    # Commands we have queued up to send to the controllers
    _name = 'hr.rfid.command'
    _description = 'Command to controller'
    _order = 'cr_timestamp desc'

    commands = [
        ('F0', _('Read System Information')),
        ('F1', _('Read/Search Card And Info')),
        ('F2', _('Read Group of Cards')),
        ('F3', _('Read Time Schedules')),
        ('F4', _('Read Holiday List')),
        ('F5', _('Read Controller Mode')),
        ('F6', _('Read Readers Mode')),
        ('F7', _('Read System Clock')),
        ('F8', _('Read Duress Mode')),
        ('F9', _('Read Input/Output Table')),
        ('FB', _('Read Inputs Flags')),
        ('FC', _('Read Anti-Passback Mode')),
        ('FD', _('Read Fire & Security Status')),
        ('FE', _('Read FireTime, Sound_Time')),
        ('FF', _('Read Output T/S Table')),
        ('D0', _('Write Controller ID')),
        ('D1', _('Add/Delete Card')),
        ('D2', _('Delete Card')),
        ('D3', _('Write Time Schedules')),
        ('D4', _('Write Holiday List')),
        ('D5', _('Write Controller Mode')),
        ('D6', _('Write Readers Mode')),
        ('D7', _('Write Controller System Clock')),
        ('D8', _('Write Duress Mode')),
        ('D9', _('Write Input/Output Table')),
        ('DA', _('Delete Last Event')),
        ('DB', _('Open Output')),
        ('DB2', _('Sending Balance To Vending Machine')),
        ('DC', _('System Initialization')),
        ('DD', _('Write Input Flags')),
        ('DE', _('Write Anti-Passback Mode')),
        ('DF', _('Write Outputs T/S Table')),
        ('D3', _('Delete Time Schedule')),
        ('B3', _('Read Controller Status')),
        ('B4', _('Read/Write Hotel buttons sense')),
    ]

    statuses = [
        ('Wait', _('Command Waiting for Webstack Communication')),
        ('Process', _('Command Processing')),
        ('Success', _('Command Execution Successful')),
        ('Failure', _('Command Execution Unsuccessful')),
    ]

    errors = [
        ('-1', _('Unknown Error')),
        ('0', _('No Error')),
        ('1', _('I2C Error')),
        ('2', _('I2C Error')),
        ('3', _('RS485 Error')),
        ('4', _('Wrong Value/Parameter')),
        ('5', _('CRC Error')),
        ('6', _('Memory Error')),
        ('7', _('Cards Overflow')),
        ('8', _('Not Use')),
        ('9', _('Card Not Found')),
        ('10', _('No Cards')),
        ('11', _('Not Use')),
        ('12', _('Controller Busy, Local Menu Active or Master Card Mode in Use')),
        ('13', _('1-Wire Error')),
        ('14', _('Unknown Command')),
        ('20', _('No Response from controller (WebSDK)')),
        ('21', _('Bad JSON Structure (WebSDK)')),
        ('22', _('Bad CRC from Controller (WebSDK)')),
        ('23', _('Bridge is Currently in Use (WebSDK)')),
        ('24', _('Internal Error, Try Again (WebSDK)')),
        ('30', _('No response from the Module')),
        ('31', _('Incorrect Data Response')),
    ]

    error_codes = list(map(lambda a: a[0], errors))

    name = fields.Char(
        compute='_compute_cmd_name',
    )

    webstack_id = fields.Many2one(
        'hr.rfid.webstack',
        string='Module',
        help='Module the command is/was intended for',
        required=True,
        readonly=True,
        ondelete='cascade',
    )

    controller_id = fields.Many2one(
        'hr.rfid.ctrl',
        string='Controller',
        help='Controller the command is/was intended for',
        required=True,
        readonly=True,
        ondelete='cascade',
        index=True,
    )

    cmd = fields.Selection(
        selection=commands,
        string='Command',
        help='Command to send/have sent to the module',
        required=True,
        readonly=True,
        index=True,
    )

    cmd_data = fields.Char(
        string='Command data',
        help='Additional data sent to the controller',
        default='',
        readonly=True,
    )

    status = fields.Selection(
        selection=statuses,
        string='Status',
        help='Current status of the command',
        default='Wait',
        index=True,
    )

    error = fields.Selection(
        selection=errors,
        string='Error',
        help='If status is "Command Unsuccessful" this field is updated '
             'to the reason for why it was unsuccessful',
        default='0'
    )

    cr_timestamp = fields.Datetime(
        string='Creation Time',
        help='Time at which the command was created',
        readonly=True,
        required=True,
        default=lambda self: fields.Datetime.now(),
    )

    ex_timestamp = fields.Datetime(
        string='Execution Time',
        help='Time at which the module returned a response from the command',
    )

    request = fields.Char(
        string='Request',
        help='Request json sent to the module'
    )

    response = fields.Char(
        string='Response',
        help='Response json sent from the module',
    )

    card_number = fields.Char(
        string='Card',
        help='Card the command will do an operation for',
        size=10,
        index=True,
    )

    retries = fields.Integer(
        string='Command retries',
        help='How many times the command failed to run and has been retried',
        default=0,
    )

    pin_code = fields.Char(string='Pin Code (debug info)')
    ts_code = fields.Char(string='TS Code (debug info)', size=8)
    rights_data = fields.Integer(string='Rights Data (debug info)')
    rights_mask = fields.Integer(string='Rights Mask (debug info)')

    def _compute_cmd_name(self):
        def find_desc(cmd):
            for it in HrRfidCommands.commands:
                if it[0] == cmd:
                    return it[1]

        for record in self:
            record.name = str(record.cmd) + ' ' + find_desc(record.cmd)

    @api.autovacuum
    def _gc_clean_old_commands(self):
        self.env['hr.rfid.command'].search([('create_date','<',fields.Datetime.now() - timedelta(days=14))]).unlink()

    @api.model
    def read_controller_information_cmd(self, controller):
        return self.with_user(SUPERUSER_ID).create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F0',
        }])

    @api.model
    def synchronize_clock_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'D7',
        }])

    @api.model
    def delete_all_cards_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DC',
            'cmd_data': '0303',
        }])

    @api.model
    def delete_all_events_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'DC',
            'cmd_data': '0404',
        }])

    @api.model
    def read_readers_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F6',
        }])

    @api.model
    def read_io_table_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'F9',
            'cmd_data': '00',
        }])

    @api.model
    def read_anti_pass_back_mode_cmd(self, controller):
        return self.create([{
            'webstack_id': controller.webstack_id.id,
            'controller_id': controller.id,
            'cmd': 'FC',
        }])

    @api.model
    def create_d1_cmd(self, ws_id, ctrl_id, card_num, pin_code, ts_code, rights_data, rights_mask):
        self.create([{
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'card_number': card_num,
            'pin_code': pin_code,
            'ts_code': ts_code,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
        }])

    @api.model
    def _create_d1_cmd_relay(self, ws_id, ctrl_id, card_num, rights_data, rights_mask):
        self.create([{
            'webstack_id': ws_id,
            'controller_id': ctrl_id,
            'cmd': 'D1',
            'card_number': card_num,
            'rights_data': rights_data,
            'rights_mask': rights_mask,
        }])

    @api.model
    def add_remove_card(self, card_number, ctrl_id, pin_code, ts_code, rights_data, rights_mask):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command'].with_user(SUPERUSER_ID)

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
        ])

        if not old_cmd:
            if rights_mask != 0:
                self.create_d1_cmd(ctrl.webstack_id.id, ctrl_id, card_number,
                                   pin_code, ts_code, rights_data, rights_mask)
        else:
            new_ts_code = ''
            if str(ts_code) != '':
                for i in range(4):
                    num_old = int(old_cmd.ts_code[i*2:i*2+2], 16)
                    num_new = int(ts_code[i*2:i*2+2], 16)
                    if num_new == 0:
                        num_new = num_old
                    new_ts_code += '%02X' % num_new
            else:
                new_ts_code = old_cmd.ts_code
            write_dict = {
                'pin_code': pin_code,
                'ts_code': new_ts_code,
            }

            new_rights_data = (rights_data | old_cmd.rights_data)
            new_rights_data ^= (rights_mask & old_cmd.rights_data)
            new_rights_data ^= (rights_data & old_cmd.rights_mask)
            new_rights_mask = rights_mask | old_cmd.rights_mask
            new_rights_mask ^= (rights_mask & old_cmd.rights_data)
            new_rights_mask ^= (rights_data & old_cmd.rights_mask)

            write_dict['rights_mask'] = new_rights_mask
            write_dict['rights_data'] = new_rights_data

            if new_rights_mask == 0:
                old_cmd.unlink()
            else:
                old_cmd.write(write_dict)

    @api.model
    def _add_remove_card_relay(self, card_number, ctrl_id, rights_data, rights_mask):
        ctrl = self.env['hr.rfid.ctrl'].browse(ctrl_id)
        commands_env = self.env['hr.rfid.command']

        old_cmd = commands_env.search([
            ('cmd', '=', 'D1'),
            ('status', '=', 'Wait'),
            ('card_number', '=', card_number),
            ('controller_id', '=', ctrl.id),
        ])

        if not old_cmd:
            self._create_d1_cmd_relay(ctrl.webstack_id.id, ctrl_id, card_number, rights_data, rights_mask)
        else:
            if ctrl.mode == 3:
                new_rights_data = rights_data
                new_rights_mask = rights_mask
            else:
                new_rights_data = (rights_data | old_cmd.rights_data)
                new_rights_data ^= (rights_mask & old_cmd.rights_data)
                new_rights_data ^= (rights_data & old_cmd.rights_mask)
                new_rights_mask = rights_mask | old_cmd.rights_mask
                new_rights_mask ^= (rights_mask & old_cmd.rights_data)
                new_rights_mask ^= (rights_data & old_cmd.rights_mask)

            old_cmd.write({
                'rights_mask': new_rights_mask,
                'rights_data': new_rights_data,
            })

    @api.model
    def add_card(self, door_id, ts_id, pin_code, card_id):
        door = self.env['hr.rfid.door'].browse(door_id)
        time_schedule = self.env['hr.rfid.time.schedule'].browse(ts_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        card_number = card.number

        if door.controller_id.is_relay_ctrl():
            return self._add_card_to_relay(door_id, card_id)

        for reader in door.reader_ids:
            ts_code = [0, 0, 0, 0]
            ts_code[reader.number-1] = time_schedule.number
            ts_code = '%02X%02X%02X%02X' % (ts_code[0], ts_code[1], ts_code[2], ts_code[3])
            self.add_remove_card(card_number, door.controller_id.id, pin_code, ts_code,
                                 1 << (reader.number-1), 1 << (reader.number-1))

    @api.model
    def _add_card_to_relay(self, door_id, card_id):
        door = self.env['hr.rfid.door'].browse(door_id)
        card = self.env['hr.rfid.card'].browse(card_id)
        ctrl = door.controller_id

        if ctrl.mode == 1:
            rdata = 1 << (door.number - 1)
            rmask = rdata
        elif ctrl.mode == 2:
            rdata = 1 << (door.number - 1)
            if door.reader_ids.number == 2:
                rdata *= 0x10000
            rmask = rdata
        elif ctrl.mode == 3:
            rdata = door.number
            rmask = -1
        else:
            raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                             % (ctrl.name, ctrl.mode))

        self._add_remove_card_relay(card.number, ctrl.id, rdata, rmask)

    @api.model
    def remove_card(self, door_id, pin_code, card_number=None, card_id=None):
        door = self.env['hr.rfid.door'].browse(door_id)

        if card_id is not None:
            card = self.env['hr.rfid.card'].browse(card_id)
            card_number = card.number

        if door.controller_id.is_relay_ctrl():
            return self._remove_card_from_relay(door_id, card_number)

        for reader in door.reader_ids:
            self.add_remove_card(card_number, door.controller_id.id, pin_code, '00000000',
                                 0, 1 << (reader.number-1))

    @api.model
    def _remove_card_from_relay(self, door_id, card_number):
        door = self.env['hr.rfid.door'].browse(door_id)
        ctrl = door.controller_id

        if ctrl.mode == 1:
            rmask = 1 << (door.number - 1)
        elif ctrl.mode == 2:
            rmask = 1 << (door.number - 1)
            if door.reader_ids.number == 2:
                rmask *= 0x10000
        elif ctrl.mode == 3:
            rmask = -1
        else:
            raise exceptions.ValidationError(_('Controller %s has mode=%d, which is not supported!')
                                             % (ctrl.name, ctrl.mode))

        self._add_remove_card_relay(card_number, ctrl.id, 0, rmask)

    @api.model
    def change_apb_flag(self, door, card, can_exit=True):
        if door.number == 1:
            rights = 0x40  # Bit 7
        else:
            rights = 0x20  # Bit 6
        self.add_remove_card(card.number, door.controller_id.id, card.get_owner().hr_rfid_pin_code,
                             '00000000', rights if can_exit else 0, rights)

    @api.model
    def _update_commands(self):
        failed_commands = self.search([
            ('status', '=', 'Process'),
            ('cr_timestamp', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

        failed_commands = self.search([
            ('status', '=', 'Wait'),
            ('cr_timestamp', '<', str(fields.datetime.now() - timedelta(minutes=1)))
        ])

        for it in failed_commands:
            it.write({
                'status': 'Failure',
                'error': '30',
            })

    @api.model
    def _sync_clocks(self):
        ws_env = self.env['hr.rfid.webstack']
        # commands_env = self.env['hr.rfid.command']

        controllers = ws_env.search([('active', '=', True)]).mapped('controllers').synchronize_clock_cmd()

        # for ctrl in controllers:
        #     commands_env.create([{
        #         'webstack_id': ctrl.webstack_id.id,
        #         'controller_id': ctrl.id,
        #         'cmd': 'D7',
        #     }])

    @api.model
    def _read_statuses(self):
        ctrl_env = self.env['hr.rfid.ctrl']
        commands_env = self.env['hr.rfid.command']

        controllers = ctrl_env.search([('read_b3_cmd', '=', True)])

        for ctrl in controllers:
            commands_env.create({
                'webstack_id': ctrl.webstack_id.id,
                'controller_id': ctrl.id,
                'cmd': 'B3',
            })

    def _check_save_comms(self, vals):
        save_comms = self.env['ir.config_parameter'].sudo().get_param('hr_rfid.save_webstack_communications')
        if save_comms != 'True':
            if 'request' in vals:
                vals.pop('request')
            if 'response' in vals:
                vals.pop('response')

    @api.model_create_multi
    def create(self, vals_list: list):
        def find_last_wait(_cmd, _vals):
            ret = self.search([
                ('webstack_id', '=', _vals['webstack_id']),
                ('controller_id', '=', _vals['controller_id']),
                ('cmd', '=', _cmd),
                ('status', '=', 'Wait'),
            ])
            if len(ret) > 0:
                return ret[-1]
            return ret

        records = self.env['hr.rfid.command']
        for vals in vals_list:
            self._check_save_comms(vals)

            cmd = vals['cmd']

            if cmd not in [ 'DB', 'D9', 'D5', 'DE', 'D7', 'F0', 'FC', 'D6', 'B3' ]:
                records += super(HrRfidCommands, self).create([vals])
                continue

            res = find_last_wait(cmd, vals)

            if len(res) == 0:
                records += super(HrRfidCommands, self).create([vals])
                continue

            cmd_data = vals.get('cmd_data', False)

            if cmd == 'DB':
                if res.cmd_data[0] == cmd_data[0] and res.cmd_data[1] == cmd_data[1]:
                    res.cmd_data = cmd_data
                    continue
            elif cmd in [ 'D9', 'D5', 'DE', 'D6' ]:
                res.cmd_data = cmd_data
                continue
            elif cmd in [ 'D7', 'F0', 'FC', 'B3' ]:
                continue

            records += super(HrRfidCommands, self).create([vals])

        return records

    def write(self, vals):
        self._check_save_comms(vals)

        if 'error' in vals and vals['error'] not in self.error_codes:
            vals['error'] = '-1'

        return super(HrRfidCommands, self).write(vals)
    


