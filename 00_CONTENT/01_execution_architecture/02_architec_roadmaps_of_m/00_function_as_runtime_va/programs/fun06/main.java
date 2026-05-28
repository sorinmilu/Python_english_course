import java.util.function.IntUnaryOperator;

public class Main {
    static IntUnaryOperator makeMultiplier(int factor) {
        return value -> value * factor;
    }

    public static void main(String[] args) {
        IntUnaryOperator timesThree = makeMultiplier(3);

        System.out.println(timesThree.applyAsInt(10));
    }
}
