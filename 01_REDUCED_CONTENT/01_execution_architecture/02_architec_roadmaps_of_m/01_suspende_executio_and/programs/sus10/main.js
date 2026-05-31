function* accumulator() {
    let total = 0;

    while (true) {
        const value = yield total;
        total += value;
    }
}

const acc = accumulator();

console.log(acc.next().value);   // 0
console.log(acc.next(5).value);  // 5
console.log(acc.next(7).value);  // 12
