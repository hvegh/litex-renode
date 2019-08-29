#!/usr/bin/env python3
import argparse
import collections
import json

from litex.configuration import Configuration

configuration = None


def mk_obj():
    """
    Makes an object of dicts and lists from the registers var

    """

    def make_dict():
        return collections.defaultdict(make_dict);

    def set_path(d, path, value):
        if path[-1] in ['reset', 'issue', 'en']: return
        for key in path[:-1]:
            d = d[key]
        d[path[-1]] = value

    the_dict = make_dict()
    for register in configuration.registers:
        set_path(
                the_dict,
                register.split('_'),
                configuration.registers[register],
                )

    return the_dict


def crawl(d):

    # normalize
    # look for in1:v in2:v and change to in:[v,v]

    # are we on a leaf?
    if not hasattr(d,'keys'): return

    # look for fooN keys
    keys=[]
    for k in d:
        crawl(d[k])
        if k in ['fx2']: continue # special cases: fx2 is not a 0,1,2
        if k[-1].isdigit():
            keys.append(k)

    # consolodate them into foo[0,1,2]
    keys.sort()
    for k in keys:
        # grab the value and remove the fooN item
        v=d.pop(k)
        # split into foo and N
        k,n=k[:-1],k[-1]
        # make a foo list
        if n=='0':
            d[k]=[]
        # append all the values to the foo list
        d[k].append(v)


def mk_json(filepath):
    """ writes json file for the moc server to serve.

    Args:
        filepath (string): path to the file lines should be written to
                           or '-' to write to a standard output

    the module's registers var data is turned into an object
    and serialized to a .json file.
    """

    o = mk_obj()
    crawl(o)

    with open(filepath, 'w') as f:
        json.dump(o, f, indent=2)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('conf_file',
                        help='CSV configuration generated by LiteX')
    parser.add_argument('--json-file', action='store',
                        help='Output json file for moc server')
    args = parser.parse_args()

    return args


def main():
    global configuration
    args = parse_args()

    configuration = Configuration(args.conf_file)

    if args.json_file:
        mk_json(args.json_file)


if __name__ == '__main__':
    main()