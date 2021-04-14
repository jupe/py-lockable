#! python3

import socket
import argparse
import os
import sys
import json
from lockable import Lockable
import subprocess


def get_args():
    parser = argparse.ArgumentParser(
        description='run given command while suitable resource is allocated.\n'
                    'Usage example: lockable --requirements {"online":true} echo using resource: $ID',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--lock-folder',
                        default='.',
                        help='lock folder')
    parser.add_argument('--resources',
                        default='./resources.json',
                        help='Resources file')
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
    args = get_args()
    if not args.command:
        raise KeyError('command is mandatory')
    lockable = Lockable(hostname=args.hostname, resource_list_file=args.resources, lock_folder=args.lock_folder)
    with lockable.auto_lock(args.requirements, timeout_s=args.timeout) as resource:
        env = os.environ.copy()
        for key in resource.resource_info.keys():
            env[key.upper()] = str(resource.resource_info.get(key))
        print(json.dumps(env))
        command = ' '.join(args.command)
        process = subprocess.Popen(command,
                                   env=env,
                                   shell=True)
        process.wait()
        return process.returncode


if __name__ == '__main__':
    sys.exit(main())
