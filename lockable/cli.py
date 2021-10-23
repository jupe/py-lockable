#! python3
"""
Lockable CLI interface
"""

import socket
import argparse
import os
import sys
import json
import subprocess
from lockable import Lockable


def get_args():
    """ Get parsed arguments """
    parser = argparse.ArgumentParser(
        description='run given command while suitable resource is allocated.\n'
                    'Usage example: lockable --requirements {"online":true} '
                    'echo using resource: $ID',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--validate-only',
                        action="store_true",
                        default=False,
                        help='Only validate resources.json')
    parser.add_argument('--lock-folder',
                        default='.',
                        help='lock folder')
    parser.add_argument('--resources',
                        default='./resources.json',
                        help='Resources file (utf-8) or http uri')
    parser.add_argument('--timeout',
                        default=1,
                        help='Timeout for trying allocate suitable resource')
    parser.add_argument('--hostname',
                        default=socket.gethostname(),
                        help='Hostname')
    parser.add_argument('--requirements',
                        default="{}",
                        help='requirements as json string')
    parser.add_argument('command', nargs='*',
                        help='Command to be execute during device allocation')

    return parser.parse_args()


def main():
    """ CLI application """
    args = get_args()
    if not args.command:
        print('command is mandatory')
        sys.exit(1)
    lockable = Lockable(hostname=args.hostname,
                        resource_list_file=args.resources,
                        lock_folder=args.lock_folder)

    if args.validate_only:
        sys.exit(0)

    with lockable.auto_lock(args.requirements, timeout_s=args.timeout) as allocation:
        resource = allocation.resource_info
        env = os.environ.copy()
        for key in resource.keys():
            env[key.upper()] = str(resource.get(key))
        print(json.dumps(env))
        command = ' '.join(args.command)
        # pylint: disable=consider-using-with
        process = subprocess.Popen(command,
                                   env=env,
                                   shell=True)
        process.wait()
    sys.exit(process.returncode)


if __name__ == '__main__':  # pragma: no cover
    main()
