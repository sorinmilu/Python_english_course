import java.util.stream.IntStream;

public class Main {
    public static void main(String[] args) {
        IntStream.iterate(1, x -> x + 1)
                 .limit(3)
                 .forEach(System.out::println);
    }
}
