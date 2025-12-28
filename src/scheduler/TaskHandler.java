package scheduler;

public interface TaskHandler {
    public String execute(String payload);
    default void setLogListener(java.util.function.Consumer<String> listener) {}
}
