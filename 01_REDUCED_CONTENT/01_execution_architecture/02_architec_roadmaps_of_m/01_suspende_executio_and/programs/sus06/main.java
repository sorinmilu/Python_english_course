import java.util.*;

public class Main {
    public static void main(String[] args) {
        Queue<StepTask> tasks = new ArrayDeque<>();

        tasks.add(new CounterTask("A", 3));
        tasks.add(new CounterTask("B", 3));

        while (!tasks.isEmpty()) {
            StepTask task = tasks.remove();

            if (task.step()) {
                tasks.add(task);
            }
        }
    }
}
