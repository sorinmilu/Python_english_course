async function loadData() {
    console.log("before request");

    const response = await fetch("/data.json");
    const data = await response.json();

    console.log(data);
}

loadData();

console.log("after scheduling");
