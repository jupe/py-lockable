# lockable

[![CircleCI](https://circleci.com/gh/jupe/py-lockable/tree/master.svg?style=svg)](https://circleci.com/gh/jupe/py-lockable/tree/master)
[![PyPI version](https://badge.fury.io/py/lockable.svg)](https://pypi.org/project/lockable/)
[![Coverage Status](https://coveralls.io/repos/github/jupe/pytest-lockable/badge.svg)](https://coveralls.io/github/jupe/py-lockable)

Resource locking module for python.

Originally designed for following projects:
* [pytest-lockable](https://github.com/jupe/pytest-lockable)
* [robot-lockable](https://github.com/jupe/robot-lockable)


Module provides python API and simple CLI interface.

Resource is released in following cases:
* process ends
* when context ends when `lockable.auto_lock(..)` is used
* allocation.unlock() is called
* lockable.unlock(<allocation>) is called

# CLI interface

```
% lockable --help
usage: lockable [-h] [--validate-only] [--lock-folder LOCK_FOLDER] [--resources RESOURCES]
                [--timeout TIMEOUT] [--hostname HOSTNAME]
                [--requirements REQUIREMENTS]
                [command [command ...]]

run given command while suitable resource is allocated.
Usage example: lockable --requirements {"online":true} echo using resource: $ID

positional arguments:
  command               Command to be execute during device allocation

optional arguments:
  -h, --help            show this help message and exit
  --validate-only       Only validate resources.json
  --lock-folder LOCK_FOLDER
                        lock folder
  --resources RESOURCES
                        Resources file
  --timeout TIMEOUT     Timeout for trying allocate suitable resource
  --hostname HOSTNAME   Hostname
  --requirements REQUIREMENTS
                        requirements as json string

```

# API's

Constructor
```python
lockable = Lockable([hostname], [resource_list_file], [lock_folder])
```

Allocation
```python
allocation = lockable.lock(requirements, [timeout_s])
print(allocation.resource_info)
print(allocation.resource_id)
allocation.unlock()
# or using resource info
lockable.unlock(allocation)
```

or using context manager which unlock automatically
```python
with lockable.auto_lock(requirements, [timeout_s]) as allocation:
    print(allocation.resource_info)
```
