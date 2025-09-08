# lockable

[![CI](https://github.com/jupe/py-lockable/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/jupe/py-lockable/actions/workflows/ci.yml?query=branch%3Amaster)
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

Resources data provider support following mechanisms:
* `resources.json` file in file system
* python list of dictionaries
* http uri which points to API and is used with HTTP GET method. API should provide `resources.json` data as json object.

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
                        Resources file (utf-8) or http uri
  --timeout TIMEOUT     Timeout for trying allocate suitable resource
  --hostname HOSTNAME   Hostname
  --requirements REQUIREMENTS
                        requirements as json string

```

# API's

Constructor
```python
lockable = Lockable([hostname], [resource_list_file], [resource_list], [lock_folder])
```

Allocation
```python
allocation_context = lockable.lock(requirements, [timeout_s])
print(allocation_context.resource_info)
print(allocation_context.resource_id)
allocation_context.unlock()
# or using resource info
lockable.unlock(allocation_context)
```

Allocation context contains following API:
* `requirements: dict` Original requirements for allocation
* `resource_info: dict` Allocated resource information
* `unlock(): func`  release resource lock function
* `allocation_queue_time: timedelta` How long waited before allocation
* `allocation_start_time: datetime` when allocation was started
* `release_time: datetime` when allocation was ended
* `alloc_id: str` allocation id
* `allocation_durations: timedelta` how long time allocation takes

or using context manager which unlock automatically
```python
with lockable.auto_lock(requirements, [timeout_s]) as allocation:
    print(allocation.resource_info)
```

Resource requirements are evaluated using
[mongoquery](https://github.com/reuben/mongoquery/), so MongoDB-style
operators like `$in` and `$gt` are supported when selecting resources.

**Tips:**

You can allocate also offline devices by set requirements `"online": None` .
You can ignore also `hostname` same same way by  setting it to  None`
