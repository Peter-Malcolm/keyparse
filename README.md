# keyparse
parse keys by describing their structure. 

Given a path like this: 
```diff
- folder1/folder2/
+ partition1=one/partition=two/
? complex_filename.with.multiple.extensions.tar.gz
```

We want to make a dict with minimal effort:
```python
parsed = {
  'first_folder': 'folder1',
  'second_folder': folder2'.
  'partition1': 'one',
  'partition2': 'two',
  'file_base': 'complex_filename'
  'ext': 'tar.gz'
}
```

The code to do this would be: 
```python
# We some keys
key='folder1/folder2/partition1=one/partition=two/complex_filename.with.multiple.extensions.tar.gz
key2='folder1/folder2/partition1=won/partition=too/another_filename.with.possiblydifferent.extensions.tar.gz

# So build the parser:
parser = Keyparser(
  dirs=['first_folder', 'second_folder'],
  partitions=['partition1','partition2'],
  file=[('file_base', '[^.]+'), 
        ('_1', '\w+\.\w+\.\w+'), # elements starting with _ are ignored
        ('ext','\.\w+\.\w+')]
  )

# then use it
parser.parse(key)

# obviously it is reuseable
parser.parse(key2)

# This will return parsed as above and something similar for key2
```
