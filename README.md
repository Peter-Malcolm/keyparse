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
