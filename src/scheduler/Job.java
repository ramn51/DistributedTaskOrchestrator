package scheduler;

import java.util.Comparator;
import java.util.UUID;

public class Job implements Comparable<Job> {
    public enum Status{
        PENDING, RUNNING, COMPLETED, FAILED, DEAD
    }

    public static final int PRIORITY_LOW = 0;
    public static final int PRIORITY_NORMAL = 1;
    public static final int PRIORITY_HIGH = 2;

    private String id;
    private String payload;
    private int retryCount;
    private Status status;

    private final int priority;
    private final long scheduledTime;

    public Job(String payload) {
        this(payload, PRIORITY_NORMAL, 0);
    }

    public Job(String payload, int priority, long delayInMs){
        this.payload = payload;
        this.id = UUID.randomUUID().toString();
        this.retryCount = 0;
        this.status = Status.PENDING;
        this.priority = priority;
        this.scheduledTime = System.currentTimeMillis() + delayInMs;
    }

    public long getScheduledTime() { return scheduledTime; }

    public void setStatus(Status status) {
        this.status = status;
    }

    public Status getStatus() {
        return status;
    }

    public void incrementRetry() {
        this.retryCount++;
    }

    public int getRetryCount() {
        return retryCount;
    }

    public String getPayload() {
        return payload;
    }

    public String getId() {
        return id;
    }

    @Override
    public int compareTo(Job other) {
        return Integer.compare(other.priority, this.priority);
    }

    @Override
    public String toString() {
        return String.format("[%s] Job %s (Retries: %d)", status, id, retryCount);
    }
}
