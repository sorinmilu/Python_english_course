function* countUpTo(limit) {
    let current = 1;

    while (current <= limit) {
        yield current;
        current += 1;
    }
}

const g = countUpTo(3);

console.log(g.next()); // { value: 1, done: false }
console.log(g.next()); // { value: 2, done: false }
console.log(g.next()); // { value: 3, done: false }
console.log(g.next()); // { value: undefined, done: true }
