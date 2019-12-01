import doctest
import re
from typing import Union, Dict, List, Tuple

PatternSpec = Union[str, Tuple[str, str]]
Path = str


class KeyParser:
    """ Parses keys using regex with increasing sophistication.
    regex matches against the entire key.

    Keys are made from directories, then partitions, then the filename.

    The directories and partitions are optional.

    **Worked Examples**

    At its most basic, just specify the key names. KeyParser will supply
    default regexes for you.

    >>> KeyParser(
    ...   dirs=['one', 'two'],
    ...   file=['filename'],
    ... ).parse("hello/world/file.csv")
    {'one': 'hello', 'two': 'world', 'filename': 'file.csv'}

    Partitions are parsed as expected:

    >>> KeyParser(
    ...     dirs=['one'],
    ...     partitions=['two'],
    ...     file=['filename'],
    ... ).parse("1/two=2/f.csv")
    {'one': '1', 'two': '2', 'filename': 'f.csv'}

    directories and partitions are optional.

      >>> KeyParser(
      ...   partitions=['one'], file=['filename'] # no dirs
      ... ).parse("one=1/file.csv")
      {'one': '1', 'filename': 'file.csv'}

    You *do* need to include a filename:

    >>> KeyParser(dirs=['one'])
    Traceback (most recent call last):
    ...
    ValueError: file must not be empty, got None

    Sometimes you want to make the regexes specific. Just use pairs
    containing the keyname and a regular expression.
    You can narrow what the 'year' partition expects:

      >>> KeyParser(
      ...   partitions=[('year','\d{4}')], file=['filename']
      ... ).parse("year=2018/file.tar.gz")
      {'year': '2018', 'filename': 'file.tar.gz'}

    or even parse the filename:

    >>> KeyParser(
    ...     file=[('base', '[^\.]+'), ('ext', '.+')]
    ... ).parse("file.tar.gz")
    {'base': 'file', 'ext': '.tar.gz'}

    Groups starting with "_" are removed:

    >>> KeyParser(
    ...     file=[('city','[a-zA-z]+'),
    ...            ('_1', '_'), ('date', '\d{8}'),  # _1 is removed
    ...            ('_2', '_'), ('candidate', '[a-zA-Z]+'), 'file_ext']  # so is _2
    ... ).parse("Kansas_20191102_Warren.csv")
    {'city': 'Kansas', 'date': '20191102', 'candidate': 'Warren', 'file_ext': '.csv'}

    Now lets try something more realistic:

    >>> KeyParser(
    ...     dirs=['environment', 'state', 'pipeline', 'table'],
    ...     partitions=[('year', '\d{4}'), ('month', '\d{2}'), ('day', '\d{2}')],
    ...     file=['filebase', ('_1', '-'), ('date', '\d{8}'), ('ext','\.csv\.gz')],
    ...     absolute=True,
    ... ).parse('/dev/raw/boardex/directors/year=1991/month=09/day=03/a_file-19910903.csv.gz')
    {'environment': 'dev', 'state': 'raw', 'pipeline': 'boardex', 'table': 'directors', 'year': '1991', 'month': '09', 'day': '03', 'filebase': 'a_file', 'date': '19910903', 'ext': '.csv.gz'}

    nesting of groups is also permitted;

    >>> KeyParser(
    ... dirs=['one', 'two', ('three', [('three_one', '\d{2}'), ('three_two', '\d{2}')])],
    ... file= ['four']
    ... ).parse("1/2/3132/4")
    {'one': '1', 'two': '2', 'three': '3132', 'three_one': '31', 'three_two': '32', 'four': '4'}

    Time for a stress test, lets try *everything* at once!

    >>> KeyParser(
    ...     dirs=[('dir1', [('one','\d'), ('two','\d')]), 'dir2'],
    ...     partitions=[('4', [('five','\d'), ('six','\d')])],
    ...     file=[('file', [('seven','\d'), ('_1','\.'), ('eight', '\d')]), 'ext']
    ... ).parse("12/3/4=56/7.8.gz")
    {'dir1': '12', 'one': '1', 'two': '2', 'dir2': '3', 'key': '56', 'five': '5', 'six': '6', 'file': '7.8', 'seven': '7', 'eight': '8', 'ext': '.gz'}

    **Exceptions**

    An exception is raised if any of the keys is used more than once:

    >>> KeyParser(dirs=['a'], file=['a'])
    Traceback (most recent call last):
    ...
    re.error: redefinition of group name 'a' as group 2; was group 1 at position 15

    or if any of the results contain the separator character:

    >>> KeyParser(file=[('a','.+')]).parse("a/b.csv")
    Traceback (most recent call last):
    ...
    ValueError: Parsed values contain the separator '/': {'a': 'a/b.csv'}

    or if the key is an invalid identifier:

    >>> KeyParser(file=['1']).parse("b.csv")
    Traceback (most recent call last):
    ...
    re.error: bad character in group name '1' at position 4

    **Formal Specification**  # TODO: Tidy up formal spec

    This specifies a mini-language, roughly equivalent to:

    |  KEY  :=  [SEP]  [DIRS]  [PARTITIONS]  FILES
    |  DIRS  :=  DIR  SEP  [DIRS]
    |  PARTITIONS  :=  PARTITION  SEP  [PARTITIONS]
    |  EXPRS := EXPR [EXPRS]
    |  EXPR := ( [EXPRS] | "\w+" )
    |  FILES  :=  FILE  [FILES]
    |  DIR  :=  ( EXPRS | "\w+" )
    |  PARTITION  := "key" "=" ( EXPRS | "\w+" )
    |  FILE  :=  ( "[\w\.]+" | EXPRS )
    |  SEP  :=  "/"

    The terminals "\w+", "[\w\.]+", "key" and "/" are all configurable.
    """

    def __init__(self,
                 dirs: List[PatternSpec] = None,
                 partitions: List[PatternSpec] = None,
                 file: List[PatternSpec] = None,
                 absolute: bool = False,
                 separator: str = "/",
                 strict: bool = True):
        """ parses keys to form named groups. Groups starting with '_' are removed
        :param dirs: list of Patterns in either group_name or (group_name, regex) format
        :param partitions: list of Patterns in either group_name or (group_name, regex) format
        :param file: list of Patterns in either group_name or (group_name, regex) format
        :param absolute: Does the key start with the separator?
        :param separator: The character to use as the separator
        :param strict: disable strict mode to turn off checking the parsed values for the separator.
        """
        self.dirs = dirs
        self.partitions = partitions
        self.file = file
        self.absolute = absolute
        self.sep = separator
        self.strict = strict

        # Guards:
        if self.dirs is None: self.dirs = []
        if self.partitions is None: self.partitions = []  # Optional arg
        if self.file is None: raise ValueError(f"file must not be empty, got {file}")
        if not isinstance(self.file, list): raise ValueError(
            f"file must be a list, got {repr(file)}")

        # Derived Properties
        self.path_prefix = self.sep if absolute else ""
        self.path_type = "absolute" if absolute else "relative"  # for logging

        # Keep final re as string for debugging/logging
        self.pattern_str = self._build_path_pattern(
            dirs=self.dirs,
            partitions=self.partitions,
            files=self.file,  # file may have multiple parts
            separator=self.sep)

        # Compile for reuse
        self.path_pattern = re.compile(self.pattern_str)

    def _make_partition(self, p: PatternSpec) -> str:
        if type(p) == str:
            return f"{p}=(?P<{p}>\w+)"
        elif type(p) == tuple and len(p) == 2:
            key, expr = p
            if type(expr) == list:
                l_expr = "".join(self._make_dir(q) for q in expr)
                return f"{key}=(?P<key>{l_expr})"
            elif type(expr) == str:
                return f"{key}=(?P<{key}>{expr})"
            else:
                raise ValueError(
                    f"Invalid argument {expr=}, must pass either partition name or (partition name, regex)")
        else:
            raise ValueError(
                f"Invalid argument {p=}, must pass either partition name or (partition name, regex)")

    def _make_file(self, f: PatternSpec):
        if type(f) == str:  # group name
            return f"(?P<{f}>[\w+\.]+)"
        elif type(f) == tuple and len(f) == 2:  # single group
            key, expr = f
            if type(expr) == list:
                l_expr = "".join(self._make_dir(q) for q in expr)
                return f"(?P<{key}>{l_expr})"
            elif type(expr) == str:
                return f"(?P<{key}>{expr})"
            else:
                raise ValueError(
                    f"Invalid argument {expr}, must pass either regex or List[PatternSpec]")
        else:
            raise ValueError(
                f"Invalid argument {f=}, must pass one of:\nfilename, (filename, regex) or List(filename_part, part_regex)")

    def _build_path_pattern(self, dirs: List[PatternSpec], partitions: List[PatternSpec],
                            files: List[PatternSpec], separator: str) -> str:

        dirs_patterns = [self._make_dir(l) for l in dirs]
        partition_patterns = [self._make_partition(p) for p in partitions]
        file_pattern = [self._make_file(f) for f in files]

        dir_parts = [*dirs_patterns, *partition_patterns]
        directories_pattern = separator.join(dir_parts) + (separator if dir_parts else "")

        path_pattern = self.path_prefix + directories_pattern + "".join(file_pattern)
        return path_pattern

    def _make_dir(self, layer: PatternSpec) -> str:
        if type(layer) == str:
            return f"(?P<{layer}>\w+)"
        elif type(layer) == tuple and len(layer) == 2:
            k, expr = layer
            if type(expr) == list:
                l_expr = "".join(self._make_dir(q) for q in expr)
                return f"(?P<{k}>{l_expr})"
            elif type(expr) == str:
                return f"(?P<{k}>{expr})"
            else:
                raise ValueError(
                    f"Invalid argument {layer=}, must pass either dir_name name or List[PatternSpec]")
        else:
            raise ValueError(f"Invalid argument {layer=}")

    def parse(self, path: Path) -> Dict[str, str]:
        if self.absolute and not path.startswith(self.sep):
            raise ValueError(f"{path=} should start with '{self.sep}' when {self.absolute=}")
        elif not self.absolute and path.startswith(self.sep):
            raise ValueError(f"{path=} should not start with '{self.sep}' when {self.absolute=}")

        if m := re.fullmatch(self.path_pattern, path):
            groups = m.groupdict()
            if self.strict and any(self.sep in val for val in groups.values()):
                raise ValueError(
                    f"Parsed values contain the separator '{self.sep}': {groups}")
            # Filter out groups stating with "_"
            r_groups = {k: v for k, v in groups.items() if not k.startswith("_")}
            return r_groups
        else:
            pattern = self.pattern_str  # Use uncompiled version for exception.
            raise ValueError(f"{path=} did not match {self.path_type} path: \n{pattern=}")


if __name__ == '__main__':
    # Run the doctests.
    doctest.testmod()
