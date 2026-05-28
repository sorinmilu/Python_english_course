import java.util.function.Consumer;

public class Main {
    static void run(Consumer<String> callback) {
        callback.accept("event happened");
    }

    public static void main(String[] args) {
        run(message -> System.out.println(message));
    }
}
