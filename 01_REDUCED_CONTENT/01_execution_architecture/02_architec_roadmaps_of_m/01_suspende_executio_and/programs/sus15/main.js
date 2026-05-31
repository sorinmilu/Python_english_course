const fs = require("fs/promises");

async function readFile() {
    console.log("before read");

    const text = await fs.readFile("notes.txt", "utf8");

    console.log(text);
}

readFile();

console.log("after call");
