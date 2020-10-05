# lockable

Resource locking module for python.

Originally designed for following projects:
* [pytest-lockable](https://github.com/jupe/pytest-lockable)
* [robot-lockable](https://github.com/jupe/robot-lockable)

Resource is released in following cases:
* process ends
* when context ends when `lockable.auto_lock(..)` is used
* allocation.unlock() is called
* lockable.unlock(<resource>) is called

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
lockable.unlock(allocation.resource_info)
```

or using context manager which unlock automatically
```python
with lockable.auto_lock(requirements, [timeout_s]) as resource_info:
    print(resource_info)
```
