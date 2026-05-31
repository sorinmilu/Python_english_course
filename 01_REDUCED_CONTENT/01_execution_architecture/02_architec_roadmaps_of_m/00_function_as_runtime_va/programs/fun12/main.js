function makeMultiplier(factor) {
    return function (value) {
        return value * factor;
    };
}

const timesThree = makeMultiplier(3);

console.log(timesThree(10));
