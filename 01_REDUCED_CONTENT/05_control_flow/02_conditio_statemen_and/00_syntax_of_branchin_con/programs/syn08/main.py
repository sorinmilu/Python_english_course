has_ticket = True
has_secret_word = False

if has_ticket:
    print("ticket accepted")

    if has_secret_word:
        print("Nobody expects the Spanish Inquisition!")
    else:
        print("ordinary entrance")

else:
    print("no ticket, no entrance")

print("gate check finished")
