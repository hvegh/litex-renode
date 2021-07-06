#!/usr/bin/env python3
"""
Copyright (c) 2019-2020 Antmicro <www.antmicro.com>

Zephyr DTS & config overlay generator for LiteX SoC.

This script parses LiteX 'csr.csv' file and generates DTS and config
files overlay for Zephyr.
"""

import argparse

from litex_renode.configuration import Configuration

configuration = None


def disabled_handler(name):
    return """
&{} {{
    status = "disabled";
}};
""".format(name)


def ram_handler(region, **kw):

    result = """
&ram0 {{
    reg = <0x{address} {size}>;
}};
""".format(address=hex(region['address'])[2:], size=hex(region['size']))

    return result


def ethmac_handler(peripheral, **kw):
    buf = kw['buffer']()

    result = """
&{} {{
""".format(kw['reference'])

    result += """
    reg = <{} {} {} {}>;
""".format(hex(peripheral['address']),
           hex(kw['size']),
           hex(buf['address']),
           hex(buf['size']))

    if 'constants' in peripheral:
        if 'interrupt' in peripheral['constants']:
            irq_no = int(peripheral['constants']['interrupt'], 0)
            result += """
    interrupts = <{} 0>;
""".format(hex(irq_no))

    result += """
};
"""
    return result


def i2c_handler(peripheral, **kw):
    result = """
&{} {{
    reg = <{} {} {} {}>;
}};
""".format(kw['reference'],
           hex(peripheral['address']),
           hex(kw['size']),
           hex(peripheral['address'] + kw['size']),
           hex(kw['size']))

    return result


def peripheral_handler(peripheral, **kw):
    result = """
&{} {{
""".format(kw['reference'])

    result += """
    reg = <{} {}>;
""".format(hex(peripheral['address']),
           hex(kw['size']))

    if 'constants' in peripheral:
        if 'interrupt' in peripheral['constants']:
            irq_no = int(peripheral['constants']['interrupt'], 0)
            result += """
    interrupts = <{} 0>;
""".format(hex(irq_no))

    result += """
};
"""
    return result


peripheral_handlers = {
    'uart': {
        'handler': peripheral_handler,
        'reference': 'uart0',
        'size': 0x18,
        'config_entry': 'UART_LITEUART'
    },
    'timer0': {
        'handler': peripheral_handler,
        'reference': 'timer0',
        'size': 0x40,
        'config_entry': 'LITEX_TIMER'
    },
    'ethmac': {
        'handler': ethmac_handler,
        'reference': 'eth0',
        'size': 0x6c,
        'buffer': lambda: configuration.mem_regions['ethmac'],
        'config_entry': 'ETH_LITEETH'
    },
    'i2c0' : {
        'handler': i2c_handler,
        'reference': 'i2c0',
        'size': 0x4,
        'config_entry': 'I2C_LITEX'
    }
}


mem_region_handler = {
    'main_ram': {
        'handler': ram_handler,
    }
}


def generate_dts():
    result = ""

    for name, peripheral in configuration.peripherals.items():
        if name not in peripheral_handlers:
            print('Skipping unsupported peripheral `{}` at {}'
                  .format(name, hex(peripheral['address'])))
            continue

        h = peripheral_handlers[name]
        result += h['handler'](peripheral, **h)

    # disable all known, but not present devices
    for name, handler in peripheral_handlers.items():
        if name in configuration.peripherals.keys():
            # this has already been generated
            continue
        result += disabled_handler(handler['reference'])

    print(configuration.mem_regions)
    for name, mem_region in configuration.mem_regions.items():
        if name not in mem_region_handler:
            print('Skipping unsupported mem_region `{}` at {}'
                  .format(name, hex(mem_region['address'])))
            continue

        h = mem_region_handler[name]
        result += h['handler'](mem_region, **h)

    return result


def generate_config():
    result = ""
    for name, handler in peripheral_handlers.items():
        if name not in configuration.peripherals.keys():
            result += "-DCONFIG_{}=n ".format(handler['config_entry'])
    return result


def print_or_save(filepath, lines):
    """ Prints given string on standard output or to the file.

    Args:
        filepath (string): path to the file lines should be written to
                           or '-' to write to a standard output
        lines (string): content to be printed/written
    """
    if filepath == '-':
        print(lines)
    else:
        with open(filepath, 'w') as f:
            f.write(lines)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('conf_file',
                        help='CSV configuration generated by LiteX')
    parser.add_argument('--dts', action='store', required=True,
                        help='Output DTS overlay file')
    parser.add_argument('--config', action='store', required=True,
                        help='Output config overlay file')
    args = parser.parse_args()

    return args


def main():
    global configuration
    args = parse_args()

    configuration = Configuration(args.conf_file)
    print_or_save(args.dts, generate_dts())
    print_or_save(args.config, generate_config())


if __name__ == '__main__':
    main()
