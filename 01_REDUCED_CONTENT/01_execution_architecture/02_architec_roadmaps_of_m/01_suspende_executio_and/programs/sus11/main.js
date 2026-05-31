console.log("start");

setTimeout(() => {
    console.log("timer A");
}, 1000);

setTimeout(() => {
    console.log("timer B");
}, 1000);

console.log("after scheduling");
