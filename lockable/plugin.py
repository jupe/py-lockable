""" Lockable library """
import random
import json
import os
import sys
from time import sleep
from contextlib import contextmanager
from pydash import filter_, merge, count_by
from func_timeout import func_timeout, FunctionTimedOut
from filelock import Timeout, FileLock


def read_resources_list(filename):
    """ Read resources json file """
    with open(filename) as json_file:
        data = json.load(json_file)
        assert isinstance(data, list), 'data is not an list'
        validate_json(data)
    return data


def validate_json(data):
    """ Validate json data """
    counts = count_by(data, lambda obj: obj.get('id'))
    no_ids = filter_(counts.keys(), lambda key: key is None)
    if no_ids:
        raise AssertionError('Invalid json, id property is missing')

    duplicates = filter_(counts.keys(), lambda key: counts[key] > 1)
    if duplicates:
        print(duplicates)
        raise AssertionError(f"Invalid json, duplicate ids in {duplicates}")


def parse_requirements(requirements_str):
    """ Parse requirements """
    if not requirements_str:
        return dict()
    try:
        return json.loads(requirements_str)
    except json.decoder.JSONDecodeError as jsonerror:
        parts = requirements_str.split('&')
        if len(parts) == 0:
            raise ValueError('no requirements given') from jsonerror
        requirements = dict()
        for part in parts:
            try:
                part.index("=")
            except ValueError:
                continue
            key, value = part.split('=')
            requirements[key] = value
        return requirements


def _try_lock(candidate, lock_folder):
    """ Function that tries to lock given candidate resource """
    resource_id = candidate.get("id")
    try:
        lock_file = os.path.join(lock_folder, f"{resource_id}.lock")
        lockable = FileLock(lock_file)
        lockable.acquire(timeout=0)
        print(f'Allocated resource: {resource_id}')

        def release():
            print(f'Release resource: {resource_id}')
            lockable.release()
            try:
                os.remove(lock_file)
            except OSError as error:
                print(error, file=sys.stderr)
        return candidate, release
    except Timeout as error:
        raise AssertionError('not success') from error


@contextmanager
def _lock_some(candidates, timeout_s, lock_folder, retry_interval):
    """ Contextmanager that lock some candidate that is free and release it finally """
    print(f'Total match local resources: {len(candidates)}, timeout: {timeout_s}')
    try:
        def doit(candidates_inner):
            while True:
                for candidate in candidates_inner:
                    try:
                        return _try_lock(candidate, lock_folder)
                    except AssertionError:
                        pass
                print('trying to lock after short period')
                sleep(retry_interval)

        resource, release = func_timeout(timeout_s, doit, args=(candidates,))
        print(f'resource {resource["id"]} allocated ({json.dumps(resource)})')
        yield resource
        release()
    except FunctionTimedOut as error:
        raise TimeoutError(f'Allocation timeout ({timeout_s}s)') from error


@contextmanager
def lock(requirements: dict,
         resource_list: list,
         timeout_s: int,
         lock_folder: str,
         retry_interval=1):
    """ Lock resource context """
    local_resources = filter_(resource_list, requirements)
    random.shuffle(local_resources)
    with _lock_some(local_resources, timeout_s, lock_folder, retry_interval) as resource:
        yield resource


def _get_requirements(requirements, hostname):
    """ Generate requirements"""
    print(f'hostname: {hostname}')
    return merge(dict(hostname=hostname, online=True), requirements)
