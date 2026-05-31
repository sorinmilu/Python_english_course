co = coroutine.create(function ()
    for i = 1, 3 do
        print("coroutine", i)
        coroutine.yield()
    end
end)

coroutine.resume(co)
print("main")
coroutine.resume(co)
print("main again")
coroutine.resume(co)
