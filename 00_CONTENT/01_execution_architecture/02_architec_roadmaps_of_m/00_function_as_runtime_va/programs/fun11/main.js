function loadUser(userId) {
    fetch("/users/" + userId)
        .then(response => response.json())
        .then(user => {
            console.log("Loaded user:", userId, user.name);
        });
}
