# lazyjson

In some situations, particularly in big data scenarios, it is necessary to extract information from a JSON file without needing to read the full content into memory. For an example, see the "Example" section below.

`lazyjson` provides a mechanism to deal with this scenario, where the JSON file is only parsed until the necessary information is found, and only that data is kept in memory.

Although the package provides ways to handle random access to the contents of the file, random access runs in linear time on the size of the file. In fact, the whole idea of the package is to support memory-lightweight **sequential processing** of the JSON file.

# Example

Imagine you have a 10GB JSON file, where the top value is an array and the various items follow a predictable structure, as illustrated in the snippet below (pretend that the top level array contains millions of items and the `snippets` key contains large arrays with potentially long strings). Imagine as well that you want to extract the identifiers associated items that are dated from January of any year.

```json
[
  {
    "identifier": "AX1999",
    "url": "http://www.example.org/url-path-with-a-slug",
    "date": {
      "year": 2020,
      "month": 1,
      "day": 1
    },
    "snippets": [
      "A happy snippet of text found in the URL",
      "Another snippet of text, this time sad",
      "Yet another",
      "And potentially many more"
    ]
  },
  // ...
]
```

Traditionally (with the standard library `json` package), you would need to read the full dataset into memory.

```py
import json

with open('data.json') as f:
  data = json.load(f)

identifiers = [
  item['identifier']
  for item in data
  if item['date']['month'] == 1
]
```

Because you're reading the full file contents into the `data` variable, the memory consumption for this snippet is quite high.

With `lazyjson`, you can keep memory usage low and still achieve the same result:

```py
import lazyjson

with open('data.json') as f:
  reader = lazyjson.Reader(f)

  identifiers = [
    item['identifier'].value()
    for item in reader
    if item['date']['month'].value() == 1
  ]
```

Notice the while the memory consumption is low, time complexity is linear for most purposes. If you want to get to a value near the end of a JSON file, the file must be fully parsed until the position you need to access. Additionally, because this is a pure python implementation, parsing is slow (I *may* change the parsing mechanism in the future to a compiled process to accelerate this).

# Comparison with `json`

As you can spot in the previous snippet of code, `lazyjson` requires you to keep the file opened while you are moving within the JSON contents. This is because no content is moved into memory unless the code does so explicitly.

Additionally, the contents of a value must be explicitly requested with the `.value()` method. *Note*: I want to change this method to something more explicit, like `materialize`, to convey the meaning that we are not simply getting the value, but actually parsing and building a JSON value, which might be costly if the value is big.

The `lazyjson.Reader` class takes a file-like object, but doesn't read its contents until requested to. You can move around the file using iteration and indexation.

Also, `lazyjson.Reader` can read "JSON streams" in addition to regular JSON files. JSON streams are files that contain JSON values in succession. The reader can navigate within these files using the `.next()` method.

```py
# Assuming file `data.json` contains
# ["an", "array"] {"an": "object"}

from lazyjson import Reader

with open('data.json') as f:
  reader = Reader(f)

  print(reader.value())  # ['an', 'array']
  reader.next()
  print(reader.value())  # {'an': 'object'}
```
# Partially valid JSON

In case your information needs from the file do not require the file to be read until the end, `lazyjson` parses only the necessary contents from the file, which means that the file does not need to be completely valid.

# Comments, trailing commas

Even though python's `json` package does not accept comments nor trailing commas, some popular packages elsewhere do. To support reading this "non-standard" data format, `lazyjson` understands double-slash comments and ignores trailing commas. So the following would be a valid JSON file from the point of view of this package:

```json
{
  // Comment
  "powers of two": [
    1,
    2,
    4,
    8,
    16,
    32,
  ],
}
```

# Simple documentation

The API surface of this package is simple, providing three classes:
- `Node`
- `NodeType`
- `Reader`

While you can produce instances of the `Node` class, I recommend you only instantiate `Reader` directly. `NodeType` is an enumeration class that represents the possible JSON value types.

## The `Node` class

This class represents a value in the JSON file. It deliberately does not contain a full representation of the value, particularly for strings, arrays and objects, because doing so would defeat the purpose of the package. It does, however, offer mechanisms to access those value, by allowing iteration over arrays and objects, and allowing (but not requiring) the construction, in memory, of its contents.

In the following examples, we assume `node` points to the JSON object represented below:
```json
{
  "a": [0, 1.337e3],
  "b": "string",
  "c": [true, false, null]
}
```

In general, some operations are only valid for some types (namely indexing, iterating, etc.). If the corresponding methods are called on a node of an incorrect type, a `ValueError` is raised.

### The `Node.type` attribute

Returns an instance of `NodeType` that represents the type of JSON value under this node. Possible values are:
- `NodeType.OBJECT`
- `NodeType.ARRAY`
- `NodeType.NUMBER`
- `NodeType.STRING`
- `NodeType.TRUE`
- `NodeType.FALSE`
- `NodeType.NULL`

### The `Node.value` method

Builds and returns the value of this node.

- If the node is a JSON true, false or null literal, it returns `True`, `False` or `None` respectively.
- If the node is a number, it parses and returns the number (returns an `int` if no decimal and no exponent is provided, `float` otherwise).
- If the node is a string, it parses the string, unescaping any escaped characters
- If the node is an array, it returns a python list
- If the node is an object, it returns a python dict

The inner values of arrays and objects are recursively built with the `.value` method as well.

### The `Node.__getitem__` method (`node[i]`)

For arrays and objects, returns a `Node` that represents the requested item. For arrays, you can index with integers. Negative value are allowed, but this requires parsing the entire array to determine the length of the array. For objects, you can index with strings. Indexing parses the node only until the correct item is found (except for indexing arrays with a negative value). If the item is not found, an `IndexError` is raised (for arrays) or a `KeyError` is raised (for objects).

```py
node['a'].value() # [0, 1337.0]
node['c'][0].value() # True
node['c'][-1].value() # None


node['x'] # raises KeyError
```

### The `Node.__len__` method (`len(node)`)

For arrays and objects, returns the length of the value. Determining the length parses the result but doesn't construct the items, which means it is easy on memory.

```py
len(node) # 3
len(node['a']) # 2
len(node['b']) # raises ValueError; you cannot determine the length of a string
```

### The `Node.__iter__` method (`for i in node`)

Iterates over the items in an array, or over the keys in an object. This iterates in the order the values appear in the file. Also see `Node.items`, to iterate over the keys *and* values of a JSON object.

```py
list(node) # ['a', 'b', 'c']
[i.value() > 0 for i in node['a']] # [False, True]
```

### The `Node.items` method

Iterates over the items of a JSON object. The iterator returned from this method sequentially produces pairs of type `(str, Node)`, where the first item in the key and the second item is the node representing the value associated with that key. The iterator respects the order in the file.

### The `Node.__contains__` method (`x in node`)

This defines the `in` operator. `x in node` is `True` if:
- `node` represents a JSON array and one of its inner values is equal to `x`
- `node` represents a JSON object and one of its keys is equal to `x`

```py
'a' in node # True
0 in node['a'] # True
```

### The `Node.is_*` methods

There are several of these methods, each testing the type of value the node points to:

- `Node.is_object`: Determines whether the node points to an object
- `Node.is_array`: Determines whether the node points to an array
- `Node.is_string`: Determines whether the node points to a string
- `Node.is_number`: Determines whether the node points to a number
- `Node.is_true`: Determines whether the node points to the `true` literal
- `Node.is_false`: Determines whether the node points to the `false` literal
- `Node.is_boolean`: Determines whether the node points to a boolean (`true` or `false`)
- `Node.is_null`: Determines whether the node points to the `null` literal

### A note on key uniqueness

`lazyjson` does **not** make an effort to validate that keys on objects are unique. This means that iterating over the keys of an object can produce the same key more than once; however, retrieving the actual value of a JSON object preserves only one of those key-value pairs (since the returned object is actually a python dictionary).

Additionally, because retrieving an item from an object stops when the key is *first* found in the file, and building the python dictionary likely preserves the *last* value associated with the key.

As such, when a key is repeated in a JSON object, the following can happen:
- `len(node) > len(node.value())`
- `node[key].value() != node.value()[key]`


## The `Reader` class

In the following examples, we assume `reader` to be constructed from a file whose contents are:
```json
{
  "a": [1, 2, 3]
}
true
[null, false, true]
```

### The `Reader.__init__` constructor

This class constructor takes a file-like whose contents are in the JSON format. The file should contain a JSON value or a sequence of JSON values (a-la JSON streams). It can also receive multiple files.

### The `Reader.node` attribute

Returns the node that is currently being read in the JSON stream. As a convenience, you can access the fields and methods of this node by calling them directly on the reader:

```py
reader.node.value() # {'a': [1, 2, 3]}
reader.value() # {'a': [1, 2, 3]}
```

### The `Reader.__len__` method  (`len(node)`)

Returns the length of the current node. Equivalent to `len(reader.node)`.

### The `Reader.__iter__` method (`for i in node`)

Iterates over the current node. Equivalent to `iter(reader.node)`

### The `Reader.__getattr__` method (`node.*`)

This method gets the requested attribute from `reader.node`, thus ensuring that the reader behaves in most ways like the node it is currently reading. Read the `Node` documentation to know more about this.

### The `Reader.__getitem__` method (`node[i]`)

This method implements random access to the contents of the current node. Equivalent to `reader.node[i]`. See the documentation for the `Node` class.

```py
reader['a'].value() # [1, 2, 3]
len(reader['a']) # 3
```

### The `Reader.next` method

Jumps to the next value on the JSON stream. Notice that if multiple files have been given in the constructor, this is the way to access the next files. There is no way to jump back to a previous value on the stream.

```py
reader.value() # {'a': [1, 2, 3]}
reader.next()
reader.value() # true
reader.next()
reader.value() # [None, False, True]
```

If there are no more nodes in the current file and no more files to process, this method raises a `StopIteration` exception.

### The `Reader.jump` method

Performs the `.next()` method a non-negative number of times.

```py
reader.value() # {'a': [1, 2, 3]}
reader.jump(2)
reader.value() # [None, False, True]
```

