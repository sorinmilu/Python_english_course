interface Callback {
    void call(String message);
}

class Printer implements Callback {
    public void call(String message) {
        System.out.println(message);
    }
}

class Dispatcher {
    static void run(Callback callback) {
        callback.call("event happened");
    }
}

public class Main {
    public static void main(String[] args) {
        Dispatcher.run(new Printer());
    }
}
