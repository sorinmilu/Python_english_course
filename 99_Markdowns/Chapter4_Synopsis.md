# CHAPTER: Sequential Component Data Architectures (Strings, Lists, and Tuples)

## The General Sequence Model in Python

### Ordered Component Storage and Positional Access

#### Indexing: Zero-Based Component Addressing with Positive and Negative Offsets

#### Slicing: Extracting Sub-Sequences with `[start:stop:step]`

#### Length, Membership, and Iteration: `len()`, `in`, and Sequential Traversal

### Sequence Operators and Shared Behaviors

#### Concatenation and Repetition: `+` and `*` Across Compatible Sequence Types

#### Equality and Lexicographic Comparison Rules

#### Immutability vs. Mutability as the Major Structural Split

## Text Encoding Systems, Lexical Escape Maps, and Character Representation

### Character Interoperability Standards

#### The Classical Domain: 7-Bit ASCII Codepoints (`0–127`) and the Later Confusion with 8-Bit Extended Encodings

#### The Universal Map: Unicode Codepoints as Abstract Character Numbers, Separate from Byte Encodings

#### Encoding Boundaries: UTF-8, UTF-16, and UTF-32 as Byte Representations of Unicode Text

### Native Conversion and Boundary Escape Sequences

#### Octal Literal Parsing Boundaries (`\000` Values through Base-8 Conversions)

#### Hexadecimal Literal Parsing Boundaries (`\xhh` Values through Base-16 Conversions)

#### Raw String Literals: Suppressing Most Escape Processing with the `r"..."` Prefix

### Extended Universal Codepoint Escape Access

#### Formal Lexical Extraction: Querying Literals via System Naming Maps (`\N{...}`)

#### Planar Transformations: 16-Bit Base-16 Codepoint Escapes via `\u`

#### Absolute Space Mapping: 32-Bit Base-16 Extended Codepoint Escapes via `\U`

## CPython String Memory Realities (`str`)

### Structural Abstraction of the Unicode Standard

#### Distinction Between Abstract Codepoints, Visible Glyphs, and Transmitted Byte Serializations

#### Text vs. Bytes: Why `str` Stores Text and `bytes` Stores Raw Byte Values

### CPython Memory Optimization Architecture (PEP 393)

#### The Flexible String Representation Framework: Dynamic Character Data Width Selection Based on Maximum Codepoint Value

#### Core Immutability: Fixed Heap Allocations and Read-Only Character Storage

#### Computational and Allocation Overhead of Iterative String Concatenation

#### The Interning Subsystem: Immutable String Optimization and Singly Allocated Literals inside CPython

### Structural Extraction and Evaluation

#### Indexing and Slicing: Characters as One-Character String Objects

#### Substring Evaluation Mechanisms: Step-Based Slice Offsets (`[start:stop:step]`) vs. Manual Pointer Offsets

#### String Formatting Paradigms: Variable Injection via Modern f-Strings

### String Sequence Operations

#### Searching and Membership: `in`, `.find()`, `.index()`, `.startswith()`, and `.endswith()`

#### Splitting and Joining: `.split()` and `.join()` as Core Text-Sequence Transformations

#### Replacement and Case Transformation: `.replace()`, `.lower()`, `.upper()`, and `.casefold()`

## Dynamic Pointer Arrays: The Python List Architecture (`list`)

### The Memory Layout Paradigm Contrast

#### The C Array Blueprint: Fixed, Contiguous Structures Storing Homogeneous Raw Primitive Values Directly

#### The Python List Blueprint: A Contiguous Array Storing Heterogeneous `PyObject*` References on the Heap

### CPython Dynamic Scaling Mechanics

#### Dynamic Over-Allocation Invariants: How CPython Pre-Allocates Extra Slots During List Resizing to Support Amortized O(1) Appends

#### Memory Shifting Costs: The O(N) Penalty of Arbitrary Index Insertions and Deletions (`.insert()`, `.pop()`)

### List Mutation Operations

#### Appending and Extending: `.append()` vs. `.extend()`

#### Index Assignment and Slice Assignment

#### Removing Elements: `.remove()`, `.pop()`, and `del`

#### Sorting and Reversing In Place: `.sort()` and `.reverse()`

### Deep vs. Shallow Structural Cloning

#### Assignment Is Not Copying: Shared List References with `b = a`

#### Shallow Copies: `a[:]`, `list(a)`, and `.copy()`

#### Nested Structures: Why Shallow Copying Fails for Lists Inside Lists

#### Deep Copying with `copy.deepcopy()`

## Fixed Structural Contiguity: The Tuple Architecture (`tuple`)

### Tuple Syntax and Structural Role

#### Tuple Packing: Comma-Based Construction with or Without Parentheses

#### Tuple Unpacking: Decomposing Fixed-Length Structures into Multiple Names

#### Single-Element Tuple Syntax: Why `(x,)` Is a Tuple but `(x)` Is Not

### Immutable Sequence Invariants

#### Structural Definition: Fixed-Size, Read-Only Sequential Storage of `PyObject*` Addresses

#### The Concept of Transitive Mutability: Why a Tuple Is Structurally Unalterable, Yet May Reference Internally Mutable Objects

### CPython Allocation Optimizations

#### CPython Allocation Caching: Version-Dependent Recycling Optimizations for Small Tuple Objects

#### Memory Footprint Metrics: Comparing Fixed `tuple` Layouts Against the Dynamic Tracking Buffers of `list`