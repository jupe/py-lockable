# lockable

[![CircleCI](https://circleci.com/gh/jupe/py-lockable/tree/master.svg?style=svg)](https://circleci.com/gh/jupe/py-lockable/tree/master)
[![PyPI version](https://badge.fury.io/py/lockable.svg)](https://pypi.org/project/lockable/)
[![Coverage Status](https://coveralls.io/repos/github/jupe/pytest-lockable/badge.svg)](https://coveralls.io/github/jupe/py-lockable)

Resource locking module for python.

Originally designed for following projects:
* [pytest-lockable](https://github.com/jupe/pytest-lockable)
* [robot-lockable](https://github.com/jupe/robot-lockable)

Resource is released in following cases:
* process ends
* when context ends when `lockable.auto_lock(..)` is used
* allocation.unlock() is called
* lockable.unlock(<allocation>) is called

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
