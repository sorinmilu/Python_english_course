import java.util.concurrent.atomic.AtomicInteger;

public class Main {
    public static void main(String[] args) {
        AtomicInteger count = new AtomicInteger(0);

        Runnable r = () -> {
            System.out.println(count.incrementAndGet());
        };

        r.run();
        r.run();
    }
}
