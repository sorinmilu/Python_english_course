host starts I/O operation
    stores promise continuation

I/O completes
    host queues microtask / continuation

V8 executes continuation
    async function resumes after await
