function* idGenerator(prefix) {
    let id = 1;

    while (true) {
        yield `${prefix}-${id}`;
        id += 1;
    }
}

const ids = idGenerator("user");

console.log(ids.next().value); // user-1
console.log(ids.next().value); // user-2
console.log(ids.next().value); // user-3
