package scheduler;

import java.util.*;

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

    private List<String> dependenciesIds = null;
    private Set<String> satisfiedDeps = null;

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

    public Job(String id, String payload, int priority, long delayInMs, List<String> dependenciesIds){
        this.payload = payload;
        this.id = id;
        this.retryCount = 0;
        this.status = Status.PENDING;
        this.priority = priority;
        this.scheduledTime = System.currentTimeMillis() + delayInMs;

        if(dependenciesIds != null && !dependenciesIds.isEmpty()){
            this.dependenciesIds = dependenciesIds;
            this.satisfiedDeps = new HashSet<>();
        }
    }

    public boolean isReady(){
        return dependenciesIds == null || satisfiedDeps.size() >= dependenciesIds.size();
    }

    public void resolveDependencies(String parentId){
        if(dependenciesIds!=null && dependenciesIds.contains(parentId)){
            satisfiedDeps.add(parentId);
        }
    }

    public static Job fromDagString(String jobStr){
        // Expected: ID|SKILL|DATA|PRIO|DELAY|[DEPS]
        String cleanedStr = jobStr.trim();
        String[] p = cleanedStr.split("\\|");

        if (p.length < 6) throw new IllegalArgumentException("Invalid DAG job format");

        String id = p[0].trim();
        String payload = p[1].trim() + "|" + p[2].trim();
        int priority = Integer.parseInt(p[3].trim());
        long delay = Long.parseLong(p[4].trim());

        String depRawStr = p[5].replace("[", "").replace("]", "").trim();
        List<String> deps;
        if(depRawStr.isEmpty()){
            deps = null;
        } else{
            deps = Arrays.stream(depRawStr.split(","))
                    .map(String::trim)
                    .filter(s -> !s.isEmpty())
                    .toList();
        }
        return new Job(id, payload, priority, delay, deps);
    }

    public List<String> getDependenciesIds(){
        if(dependenciesIds == null)
            return Collections.emptyList();
        else
            return dependenciesIds;
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
