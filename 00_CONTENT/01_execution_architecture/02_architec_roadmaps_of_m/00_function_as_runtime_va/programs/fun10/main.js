function attachCounter(button) {
    let count = 0;

    button.addEventListener("click", () => {
        count += 1;
        console.log("clicked", count, "times");
    });
}
