make_printer() {
    local name="$1"
    local prefix="$2"

    eval "$name() { echo '$prefix' \"\$1\"; }"
}

make_printer print_error "ERROR:"
print_error "file missing"
