const fs = require("fs");

fs.readFile("notes.txt", "utf8", function (error, data) {
    if (error) {
        console.error(error);
        return;
    }

    console.log(data);
});
