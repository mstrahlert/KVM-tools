#!/usr/bin/env python3
#
# Magnus Strahlert @ 211028
#   Parses virt-backup.conf and shows it as a compact list

import configparser
import argparse
import os

def read_config(configfile):
    config = configparser.ConfigParser()
    with open(configfile) as f:
        # This construct will warn for duplicate entries while continuing with parsing.
        # The last node entry read will be the entry shown. This matches older behaviour
        try:
            config.read_string(f.read())
        except configparser.DuplicateSectionError as err:
            print("Warning: {}".format(err))
            config = configparser.ConfigParser(strict=False)
            with open(configfile) as f:
                config.read_string(f.read())

    return config

def list_nodes(config):
    nodes = config.sections()
    nodes.remove('global')

    return nodes

def query_node(config, node):
    return config[node]

def query_global(config):
    return config['global']

def main():
    parser = argparse.ArgumentParser(description='Query information from virt-backup')
    parser.add_argument('--config', action='store', default='virt-backup.conf', nargs='*', metavar='FILE',
                        help='Input several files for comparision (default: %(default)s)')

    results = parser.parse_args()

    # Prettifying the help text. Converts the string to a list when default is used
    if (type(results.config) != type([])):
        results.config = results.config.split()

    nodes = {}

    # Read each configfile given as argument
    for configfile in results.config:
        if os.path.exists(configfile) == False:
            print("Error: Configfile {} does not exist".format(configfile))
            continue

        configuration = read_config(configfile)

        # Print header
        print("{configfile:<20} {weekday:<16} {priority:<3} {retention:<3} {time:<5} {method:<10}".format(configfile=configfile,
            weekday="Weekday", priority="Prio", retention="Ret", time="Time", method="Method"))
        for node in list_nodes(configuration):
            if node in nodes.keys():
                print("Warning: {node} already seen in {file}".format(node=node, file=nodes[node]['file']))

            # Populate a dictionary to pretty print and fill values without getting KeyError
            nodes[node] = {}
            nodes[node]['file'] = configfile
            nodes[node]['weekday'] = query_node(configuration, node).get('weekday', '*')
            nodes[node]['priority'] = query_node(configuration, node).get('priority', '')
            nodes[node]['retention'] = query_node(configuration, node).get('retention', query_global(configuration).get('retention', '?'))
            nodes[node]['time'] = query_node(configuration, node).get('time', query_global(configuration).get('start_at', '??:??'))
            nodes[node]['method'] = query_node(configuration, node).get('method', query_global(configuration).get('method', '???'))

            print("{node:<20} {weekday:<16} {priority:<3} {retention:<3} {time:<5} {method:<10}".format(node=node,
                weekday=nodes[node]['weekday'], priority=nodes[node]['priority'], retention=nodes[node]['retention'],
                time=nodes[node]['time'], method=nodes[node]['method']))

        print()

if __name__ == "__main__":
   main()
