import java.util.ArrayDeque;
import java.util.Queue;

public class EventLoop {
    private final Queue<Runnable> queue = new ArrayDeque<>();

    public void callSoon(Runnable task) {
        queue.add(task);
    }

    public void run() {
        while (!queue.isEmpty()) {
            Runnable task = queue.remove();
            task.run();
        }
    }

    public static void main(String[] args) {
        EventLoop loop = new EventLoop();

        loop.callSoon(() -> System.out.println("A"));
        loop.callSoon(() -> System.out.println("B"));
        loop.callSoon(() -> System.out.println("C"));

        loop.run();
    }
}
