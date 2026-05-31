import java.util.Iterator;
import java.util.NoSuchElementException;

class CountUpTo implements Iterator<Integer> {
    private int current = 1;
    private final int limit;

    CountUpTo(int limit) {
        this.limit = limit;
    }

    public boolean hasNext() {
        return current <= limit;
    }

    public Integer next() {
        if (!hasNext()) {
            throw new NoSuchElementException();
        }

        int value = current;
        current += 1;
        return value;
    }
}

public class Main {
    public static void main(String[] args) {
        Iterator<Integer> it = new CountUpTo(3);

        while (it.hasNext()) {
            System.out.println(it.next());
        }
    }
}
