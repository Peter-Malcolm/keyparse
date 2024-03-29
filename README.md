# keyparse
_keyparse lets you parse path-like keys by describing their structure._

\* a key may be a filepath, an s3 object, or something else entirely (results may vary).

### an example
Given a path like this: 
```diff
- folder1/folder2/
+ partition1=one/partition=two/
? complex_filename.with.multiple.extensions.tar.gz
```

Suppose we want to generate the dict below with minimal effort:
```python
parsed_key = {
  'first_folder': 'folder1',
  'second_folder': folder2'.
  'partition1': 'one',
  'partition2': 'two',
  'file_base': 'complex_filename'
  'ext': '.tar.gz'
}
```

The code to do this would be: 
```python
# We have some keys
key1 = 'folder1/folder2/partition1=one/partition=two/complex_filename.with.multiple.extensions.tar.gz
key2 = 'folder1/folder2/partition1=won/partition=too/another_filename.with.possiblydifferent.extensions.tar.gz

# first build the parser:
parser = Keyparser(
  dirs=['first_folder', 'second_folder'],
  partitions=['partition1','partition2'],
  file=[('file_base', '[^.]+'), 
        ('_1', '\.with\.\w+\.\w+'), # elements starting with _ are ignored
        ('ext','\.\w+\.\w+')]
  )

# then use it
parser.parse(key1)

# obviously it is reuseable
parser.parse(key2)

# for key1 this will return parsed_key as above and something similar for key2
```
