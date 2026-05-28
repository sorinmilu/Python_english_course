# CHAPTER: Input/Output Architecture, File Streams, and External Data Boundaries

## The I/O Boundary: From Runtime Objects to External Systems

### Programs as Data Consumers and Data Producers

#### Runtime Memory vs. Persistent Storage: Why Variables Disappear but Files Remain

#### Standard Streams: `stdin`, `stdout`, and `stderr` as Process-Level Communication Channels

#### C Comparison: `printf()`, `scanf()`, File Descriptors, and Python’s Higher-Level Stream Objects

### The Operating System Mediation Layer

#### Why Python Does Not Read Disks Directly: System Calls, File Handles, and Kernel Buffers

#### File Descriptors vs. Python File Objects: Native Resource Handles Wrapped in Managed Runtime Objects

#### Buffering Layers: Reducing Expensive Kernel Transitions Through Intermediate Memory Buffers

## File Opening, Closing, and Resource Lifetime

### The `open()` Function and File Object Construction

#### Path Argument, Mode Argument, Encoding Argument, and Runtime File Object Creation

#### Read Modes, Write Modes, Append Modes, and Exclusive Creation Modes

#### Text Mode vs. Binary Mode: `str` Streams vs. `bytes` Streams

### Resource Management Invariants

#### Manual Closing with `.close()` and the Risk of Leaked File Handles

#### Context Managers: The `with` Statement as Structured Resource Lifetime Control

#### The `__enter__()` / `__exit__()` Protocol Behind `with`

#### Exception-Safe Cleanup: Why File Handles Close Even When Errors Occur Inside the Block

## Text File Reading and Writing

### Reading Textual Data

#### Full-File Loading with `.read()` and Memory Consumption Boundaries

#### Line-Based Reading with `.readline()` and Iteration over File Objects

#### Batch Line Loading with `.readlines()` and List Materialization Costs

### Writing Textual Data

#### Writing Strings with `.write()`

#### Writing Multiple Lines with `.writelines()`

#### Newline Management: Explicit `\n`, Platform Differences, and Universal Newline Translation

### Encoding and Decoding Boundaries

#### Text Encoding Revisited: Translating Between `str` Objects and Stored Byte Sequences

#### Common Encoding Choices: UTF-8 as the Default Modern Interchange Encoding

#### Encoding Failure Modes: `UnicodeDecodeError`, `UnicodeEncodeError`, and Error Handling Strategies

## Binary File Reading and Writing

### Byte-Oriented Data Streams

#### Binary Mode as Raw Byte Transfer Without Text Decoding

#### The `bytes` Object: Immutable Byte Sequences Distinct from `str`

#### The `bytearray` Object: Mutable Byte Buffers for Incremental Modification

### Binary Access Patterns

#### Reading Fixed-Size Chunks for Large Files

#### Writing Byte Buffers to External Storage

#### Random Access with `.seek()` and `.tell()`

## Filesystem Path Architecture

### Paths as Structured Filesystem References

#### String Paths vs. `pathlib.Path` Objects

#### Absolute Paths, Relative Paths, and Current Working Directory Resolution

#### Platform Separators: Windows Backslashes, POSIX Slashes, and Portable Path Construction

### Filesystem Inspection and Manipulation

#### Checking Existence, File Type, and Directory Type

#### Creating Directories and Parent Directory Chains

#### Listing Directory Contents and Iterating over Filesystem Entries

#### Renaming, Moving, and Deleting Files Safely

## Structured Data Interchange

### JSON Data Boundaries

#### JSON as Text-Based Tree Serialization: Objects, Arrays, Strings, Numbers, Booleans, and Null

#### Loading JSON into Python Dictionaries and Lists with `json.load()` and `json.loads()`

#### Writing Python Structures Back to JSON with `json.dump()` and `json.dumps()`

#### JSON Type Mapping Boundaries: `None` vs. `null`, `dict` vs. Object, `list` vs. Array

### CSV Tabular Data

#### CSV as Row-Oriented Text with Delimited Fields

#### Reading CSV Files with `csv.reader`

#### Dictionary-Based Row Access with `csv.DictReader`

#### Writing CSV Rows with `csv.writer` and `csv.DictWriter`

#### Quoting, Escaping, Delimiters, and Newline Handling

## Error Handling in I/O Operations

### Expected Failure Modes

#### Missing Files and `FileNotFoundError`

#### Permission Failures and `PermissionError`

#### Invalid Paths, Locked Files, and Platform-Specific Filesystem Constraints

### Defensive I/O Patterns

#### EAFP File Access: Trying the Operation and Handling the Exception

#### LBYL File Access: Checking Conditions Before Opening

#### Atomicity Concerns: Why Existence Checks Can Become Invalid Before Use

## Practical External Data Pipelines

### Streaming Large Inputs

#### Processing Files Line by Line Without Loading Entire Contents into Memory

#### Chunked Binary Processing for Large Media or Archive Files

### Transforming External Data

#### Read-Transform-Write Pipelines

#### Temporary Files and Safe Output Replacement

#### Separating Parsing, Processing, and Serialization Functions