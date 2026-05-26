# Hash-based collections and associative mappings

## 5.1 Unordered Unique Domains: The Set Architecture (`set`)

### 5.1.1 Mathematical Foundations and Structural Syntax
#### 5.1.1.1 Defining Unique Unordered Domains using the Curly-Brace `{}` Construct
#### 5.1.1.2 Instantiation Boundaries: Differentiating Empty Set Initialization `set()` from Empty Dictionary Literal Declarations `{}`

### 5.1.2 Constraints of Element Ingestion and Runtime Engines
#### 5.1.2.1 The Uniqueness Invariant: Automated De-duplication Mechanics at Runtime
#### 5.1.2.2 The Hashability Criterion: Object Identity (`id()`), Value Equality (`__eq__`), and Hash Stability (`__hash__`) Requirements
#### 5.1.2.3 CPython Open-Addressing Architecture: How the Runtime Allocates the Underlying Set Hash Table Array and Resolves Collisions via Dummy/Pseudo-Random Probing
#### 5.1.2.4 Algorithmic Efficiency Matrix: Amortized O(1) Membership Lookups vs. the O(N) Shifting Penalties of Sequential Array Traversal

## 5.2 Set Mathematical Operators and Mutator Methods

### 5.2.1 Fundamental Set Calculations
#### 5.2.1.1 The Union Operator (`|`) and Method Equivalent (`.union()`)
#### 5.2.1.2 The Intersection Operator (`&`) and Method Equivalent (`.intersection()`)
#### 5.2.1.3 The Difference Operator (`-`) and Method Equivalent (`.difference()`)
#### 5.2.1.4 The Symmetric Difference Operator (`^`) and Method Equivalent (`.symmetric_difference()`)

### 5.2.2 In-Place Memory Mutation (Destructive Updates)
#### 5.2.2.1 Modifying Heap Collections Directly via `.intersection_update()`
#### 5.2.2.2 Differential Mutator Operations via `.difference_update()`

### 5.2.3 Structural Relationship Evaluation
#### 5.2.3.1 Containment and Scope Testing: Identifying Subsets (`.issubset()`) and Supersets (`.issuperset()`)
#### 5.2.3.2 Intersection Disjoint Verification via `.isdisjoint()`

## 5.3 Dictionaries (`dict`) — Key-Value Associated Mapping

### 5.3.1 Foundations of Associative Mapping
#### 5.3.1.1 Structural Syntax: The Key-Value Paradigm and Curly-Brace `{}` Literals
#### 5.3.1.2 Integrity Constraints: Why Dictionary Keys Must Be Immutable and Universally Hashable
#### 5.3.1.3 Value Flexibility: Storing Arbitrary, Nested Data Types and Mutable Heap Objects

### 5.3.2 CPython Architectural Evolution
#### 5.3.2.1 The Classic Hash Table Design: Unordered Item Management via Sparse Arrays (Pre-Python 3.7)
#### 5.3.2.2 The Modern Compact Dictionary: How CPython Splits Storage into a Dense Key/Value Array and a Small Index Array to Preserve Insertion Order and Reduce Memory Footprint (Post-Python 3.7 / Raymond Hettinger Blueprint)
#### 5.3.2.3 Algorithmic Efficiency Matrix: Amortized O(1) Complexity for Key Insertion, Value Retrieval, and Structural Deletion

### 5.3.3 Querying, Manipulating, and Mutating Dictionary States
#### 5.3.3.1 Explicit Lookups and the `KeyError` Boundary vs. Safe Ingestion via the `.get()` Method and Default Values
#### 5.3.3.2 View Objects Subsystems: Interrogating `.keys()`, `.values()`, and `.items()` Dynamic Proxies
#### 5.3.3.3 The Mutation Trap: Why Mutating a Dictionary's Geometry During View Object Iteration Triggers Immediate Runtime Exceptions
#### 5.3.3.4 Dynamic Modifications: In-Place Mutation, Dictionary Merging Operators (`|`, `|=`), and Key-Value Eviction Subsystems (`.pop()`, `del`)