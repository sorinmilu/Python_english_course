has_ticket = False
has_secret_word = True

if has_ticket:
    print("ticket accepted")

    if has_secret_word:
        print("Nobody expects the Spanish Inquisition!")
    else:
        print("ordinary entrance")

else:
    print("no ticket, no entrance")

print("gate check finished")
