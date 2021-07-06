#!/usr/bin/env python3
"""
Copyright (c) 2019-2020 Antmicro <www.antmicro.com>

LiteX configuration parser.

This module provides class for parsing LiteX configuration
exported in 'csr.json' and/or 'csr.csv' files.
"""

import csv
import json
import itertools


class Configuration(object):

    def __init__(self, conf_file):
        self.peripherals = {}
        self.constants = {}
        self.registers = {}
        self.mem_regions = {}

        with open(conf_file) as csvfile:
            content = Configuration._remove_comments(csvfile)

            if conf_file.endswith('csv'):
                self._parse_csv(list(csv.reader(content)))
            elif conf_file.endswith('json'):
                self._parse_json('\n'.join(content))
            else:
                raise Exception('Unsupported configuration file format')

        self._normalize_addresses()

    @staticmethod
    def _remove_comments(data):
        for line in data:
            if not line.lstrip().startswith('#'):
                yield line

    def find_peripheral_constant(self, constant_name):
        for _csr_name in self.peripherals:
            if constant_name.startswith(_csr_name):
                local_name = constant_name[len(_csr_name) + 1:]
                return (self.peripherals[_csr_name], local_name)
        return (None, None)

    def _parse_json(self, data):
        """ Parses LiteX json file.

        Args:
            data (list): list of json file lines
        """

        j = json.loads(data)

        for _name in j['csr_bases']:
            b = j['csr_bases'][_name]
            self.peripherals[_name] = {'name': _name,
                                       'address': b,
                                       'constants': {}}

        for _name in j['csr_registers']:
            r = j['csr_registers'][_name]
            self.registers[_name] = {'name': _name,
                                     'address': r['addr'],
                                     'size': r['size'],
                                     'r': r['type']}

        for _name in j['constants']:
            c = j['constants'][_name]
            p, ln = self.find_peripheral_constant(_name)

            if not ln:
                # if it's not a CSR-related constant, it must be a global one
                self.constants[_name] = {'name': _name, 'value': c}
            else:
                # it's a CSR-related constant
                p['constants'][ln] = c

        for _name in j['memories']:
            m = j['memories'][_name]
            self.mem_regions[_name] = {'name': _name,
                                       'address': m['base'],
                                       'size': m['size'],
                                       'type': m['type'] if 'type' in m else 'unknown'}

    def _parse_csv(self, data):
        """ Parses LiteX CSV file.

        Args:
            data (list): list of CSV file lines
        """

        # scan for CSRs first, so it's easier to resolve CSR-related constants
        # in the second pass
        for _type, _name, _address, _, __ in data:
            if _type == 'csr_base':
                self.peripherals[_name] = {'name': _name,
                                           'address': int(_address, 0),
                                           'constants': {}}

        for _type, _name, _val, _val2, _val3 in data:
            if _type == 'csr_base':
                # CSRs have already been parsed
                pass
            elif _type == 'csr_register':
                # csr_register,info_dna_id,0xe0006800,8,ro
                self.registers[_name] = {'name': _name,
                                         'address': int(_val, 0),
                                         'size': int(_val2, 0),
                                         'r': _val3}
            elif _type == 'constant':
                p, ln = self.find_peripheral_constant(_name)

                if not ln:
                    # if it's not a CSR-related constant, it must be a global one
                    self.constants[_name] = {'name': _name, 'value': _val}
                else:
                    # it's a CSR-related constant
                    p['constants'][ln] = _val

            elif _type == 'memory_region':
                self.mem_regions[_name] = {'name': _name,
                                           'address': int(_val, 0),
                                           'size': int(_val2, 0),
                                           'type': _val3}
            else:
                print('Skipping unexpected CSV entry: {} {}'.format(_type, _name))

    def _normalize_addresses(self):

        shadow_base = None
        if 'shadow_base' in self.constants:
            shadow_base = self.constants['shadow_base']['value']
            if not isinstance(shadow_base, int):
                shadow_base = int(shadow_base, 0)

        for r in itertools.chain(self.mem_regions.values(), self.registers.values(), self.peripherals.values()):
            if shadow_base is None:
                r['shadowed_address'] = None
            else:
                r['shadowed_address'] = r['address'] | shadow_base
                if r['shadowed_address'] == r['address']:
                    r['address'] &= ~shadow_base
