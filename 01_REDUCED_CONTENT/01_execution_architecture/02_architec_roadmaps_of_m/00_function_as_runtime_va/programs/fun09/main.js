const request = new XMLHttpRequest();

request.onload = function () {
    console.log(request.responseText);
};

request.open("GET", "/data.json");
request.send();
