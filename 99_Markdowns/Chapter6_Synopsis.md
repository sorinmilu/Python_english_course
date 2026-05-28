# CHAPTER: Hash-Based Collections and Associative Mappings

## Hash Tables as Non-Sequential Component Access Structures

### From Positional Access to Hash-Based Access

#### Sequential Collections: Why Lists, Tuples, and Strings Locate Components by Index

#### Hash-Based Collections: Why Sets and Dictionaries Locate Components by Hash-Derived Table Slots

### The Hash and Equality Contract

#### `__hash__()` as the Stable Integer Descriptor Used for Table Placement

#### `__eq__()` as the Equality Check Used After Candidate Slot Discovery

#### The Required Invariant: Equal Objects Must Produce Equal Hash Values

#### Hash Stability: Why Keys and Set Elements Must Not Change Their Hash-Relevant State While Stored

## Unordered Unique Domains: The Set Architecture (`set`)

### Mathematical Foundations and Structural Syntax

#### Defining Unique Unordered Domains Using the Curly-Brace `{}` Construct

#### Instantiation Boundaries: Differentiating Empty Set Initialization `set()` from Empty Dictionary Literal Declaration `{}`

#### Set Comprehensions as Hash-Based Filtering Structures

### Constraints of Element Ingestion and Runtime Engines

#### The Uniqueness Invariant: Automated De-Duplication Mechanics at Runtime

#### The Hashability Criterion: Value Equality, Hash Stability, and Table Placement Requirements

#### CPython Open-Addressing Architecture: Hash Table Slots, Collision Probing, Empty Slots, and Deleted-Entry Markers

#### Algorithmic Efficiency Matrix: Amortized O(1) Membership Lookups vs. O(N) Sequential Traversal

### Core Set Mutation Operations

#### Adding Elements with `.add()`

#### Removing Elements with `.remove()`, `.discard()`, `.pop()`, and `.clear()`

#### Membership Testing with `in`

### Immutable Set Variants

#### `frozenset` as an Immutable Hashable Set-Like Object

#### Using `frozenset` as a Dictionary Key or Set Element

## Set Mathematical Operators and Mutator Methods

### Fundamental Set Calculations

#### The Union Operator (`|`) and Method Equivalent (`.union()`)

#### The Intersection Operator (`&`) and Method Equivalent (`.intersection()`)

#### The Difference Operator (`-`) and Method Equivalent (`.difference()`)

#### The Symmetric Difference Operator (`^`) and Method Equivalent (`.symmetric_difference()`)

### In-Place Memory Mutation

#### Destructive Union Updates via `.update()`

#### Destructive Intersection Updates via `.intersection_update()`

#### Destructive Difference Updates via `.difference_update()`

#### Destructive Symmetric Difference Updates via `.symmetric_difference_update()`

### Structural Relationship Evaluation

#### Containment and Scope Testing: Identifying Subsets (`.issubset()`) and Supersets (`.issuperset()`)

#### Intersection Disjoint Verification via `.isdisjoint()`

## Dictionaries (`dict`) — Key-Value Associative Mappings

### Foundations of Associative Mapping

#### Structural Syntax: The Key-Value Paradigm and Curly-Brace `{}` Literals

#### Integrity Constraints: Why Dictionary Keys Must Be Hashable and Hash-Stable

#### Value Flexibility: Storing Arbitrary, Nested Data Types and Mutable Heap Objects

#### Membership Testing: Why `x in d` Checks Keys, Not Values

### Dictionary Construction Patterns

#### Literal Construction with `{key: value}` Pairs

#### Constructor-Based Construction with `dict()`

#### Dictionary Comprehensions as Key-Value Generation Pipelines

#### Building Dictionaries from Pair Sequences

### CPython Architectural Evolution

#### The Classic Dictionary Model: Sparse Hash Table Storage and Historically Unspecified Iteration Order

#### The Modern Compact Dictionary: Dense Entry Storage, Sparse Indexing, Memory Reduction, and Insertion-Order Preservation

#### Algorithmic Efficiency Matrix: Amortized O(1) Complexity for Key Insertion, Value Retrieval, and Structural Deletion

### Ordering Guarantees and Misconceptions

#### Dictionary Insertion Order: Preserved Order Is Not Sorted Order

#### Set Iteration Order: Why Sets Remain Unordered Even When They Appear Stable in Small Examples

### Querying, Manipulating, and Mutating Dictionary States

#### Explicit Lookups and the `KeyError` Boundary vs. Safe Access via `.get()`

#### Default Insertion Patterns with `.setdefault()`

#### View Object Subsystems: Interrogating `.keys()`, `.values()`, and `.items()` Dynamic Proxies

#### Dynamic Views: Why Dictionary Views Reflect Later Dictionary Mutations

#### The Mutation Trap: Why Mutating Dictionary Geometry During Iteration Triggers Runtime Exceptions

#### Dynamic Modifications: In-Place Mutation, Dictionary Merging Operators (`|`, `|=`), and Key-Value Eviction (`.pop()`, `del`)