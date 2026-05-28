# CHAPTER: Variables and Singular Data Types

## Identifiers and Syntax Rules for Variables

### Legal and Structural Lexer Constraints

#### Digit Restrictions: Why Identifiers Cannot Start with a Numerical Character

#### Valid Characters: Letters, Digits, Underscore (`_`), and Unicode Identifier Rules

#### Reserved Keywords: Why `def`, `class`, `import`, and Similar Tokens Cannot Be Used as Names

#### Case Sensitivity: `name`, `Name`, and `NAME` as Distinct Bindings

### Stylistic Coding Conventions

#### Alignment with the PEP 8 Style Guide

#### Readable Naming Conventions: Lowercase `snake_case` for Ordinary Variables

#### Underscore Conventions: Internal Names, Throwaway Names, and Special Method Boundaries

## Assignment and Name Binding

### Simple Assignment: Creating or Rebinding a Name

#### Assignment as Binding, Not Memory Copying

#### Reassignment: Moving a Name from One Object to Another

#### Object Sharing: Binding Multiple Names to the Same Runtime Object (`a = b`)

### Multiple Assignment and Unpacking

#### Parallel Assignment: Swapping Values with `a, b = b, a`

#### Sequence Unpacking and Arity Requirements

#### Extended Unpacking with the Star Target (`*rest`)

### Augmented Assignment

#### Numeric Augmented Assignment (`+=`, `-=`, `*=`, `/=`) as Read-Operate-Rebind for Immutable Singular Values

#### Mutation vs. Rebinding Preview for Later Mutable Containers

### Deleting Names

#### Removing a Binding with `del`

#### Name Deletion, Object Reachability, and Possible Reference Count Changes

## Singular Data Domains and Operator Precedence

### The Integer Representation Architecture (`int`)

#### Arbitrary-Precision Math Engine: Eliminating Fixed-Width Integer Overflow Boundaries

#### Dynamic Bit Scaling: CPython's Digit-Array Structural Allocation for High-Magnitude Values

#### Integer Literals: Decimal, Binary, Octal, and Hexadecimal Notation

### The Floating-Point Representation Architecture (`float`)

#### Architectural Realities: Mapping Python Floats to C Doubles via the IEEE 754 Double-Precision Binary Standard

#### Machine Epsilon and Precision Loss: The Pitfalls of Representing Base-10 Fractions in Base-2 Memory Buffers

#### Special Floating-Point Values: Infinity, Negative Infinity, and NaN

### The Complex Representation Architecture (`complex`)

#### Language-Native Integration via the Mathematical Imaginary Component `j` Literal

#### Component Access Mechanisms: Extracting `.real` and `.imag` Floating-Point Parts

#### Complex Arithmetic Boundaries: Why Ordering Comparisons Are Not Defined for Complex Numbers

### The Boolean Representation Architecture (`bool`)

#### Boolean Values as Singleton Objects: `True` and `False`

#### Boolean as a Subclass of Integer: Numeric Compatibility and Practical Warnings

#### Logical Operators vs. Bitwise Operators: `and` / `or` / `not` Compared with `&` / `|` / `~`

### The Null-Sentinel Object (`None`)

#### `None` as a Singleton Object, Not a Null Pointer

#### Absence, Default Return Values, and Missing-Value Signaling

#### Identity Testing with `is None` and `is not None`

### Numerical Operator Architecture and Precedence Graphs

#### Standard Arithmetic: Operator Dispatch and Result Object Creation

#### Division Divergence: Floating-Point Division (`/`) vs. Floor Division (`//`)

#### Modular Math (`%`) and Exponentiation (`**`) Mechanics

#### Unary Operators and Precedence Traps: `-x`, `+x`, and `-2 ** 2`

#### Parentheses as Explicit Precedence Control

## Runtime Typing Consequences in Singular Operations

### Dynamic Typing in Assignment

#### Names Do Not Have Fixed Declared Types

#### Rebinding the Same Name to Objects of Different Types

#### Runtime Type Inspection with `type()` and `isinstance()`

### Strong Typing in Operations

#### Why Heterogeneous Operations Such as `"3" + 4` Fail Instead of Silently Converting

#### Explicit Conversion with `int()`, `float()`, `complex()`, `bool()`, and `str()`

#### Numeric Promotion Boundaries: Integer, Float, Complex, and Boolean Interactions

### Structural Summary

#### Categorizing Python as a Dynamically Bound, Strongly Verified Runtime Typing Environment

#### The Practical Rule: Names Are Flexible, Objects Keep Their Runtime Type