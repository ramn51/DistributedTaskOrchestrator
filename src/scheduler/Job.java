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

    public void setId(String id){
        this.id = id;
    }

    public void setPayload(String payload){
        this.payload = payload;
    }

    public boolean isReady(){
        return dependenciesIds == null || satisfiedDeps.size() >= dependenciesIds.size();
    }

    public void resolveDependencies(String parentId){
        if(dependenciesIds!=null && dependenciesIds.contains(parentId)){
            satisfiedDeps.add(parentId);
        }
    }

//    public static Job fromDagString(String jobStr){
//        // Expected: ID|SKILL|DATA|PRIO|DELAY|[DEPS]
//        String cleanedStr = jobStr.trim();
//        String[] p = cleanedStr.split("\\|");
//
//        if (p.length < 6) throw new IllegalArgumentException("Invalid DAG job format");
//
//        String id = p[0].trim();
//        String payload = p[1].trim() + "|" + p[2].trim();
//        int priority = Integer.parseInt(p[3].trim());
//        long delay = Long.parseLong(p[4].trim());
//
//        String depRawStr = p[5].replace("[", "").replace("]", "").trim();
//        List<String> deps;
//        if(depRawStr.isEmpty()){
//            deps = null;
//        } else{
//            deps = Arrays.stream(depRawStr.split(","))
//                    .map(String::trim)
//                    .filter(s -> !s.isEmpty())
//                    .toList();
//        }
//
//        String finalPayload;
//        if (type.equalsIgnoreCase("RUN")) {
//            // Map "RUN" to "RUN_PAYLOAD" so it matches the standalone behavior
//            finalPayload = "RUN_PAYLOAD|" + data;
//        } else if (type.equalsIgnoreCase("DEPLOY")) {
//            // Map "DEPLOY" to "DEPLOY_PAYLOAD"
//            finalPayload = "DEPLOY_PAYLOAD|" + data;
//        } else {
//            finalPayload = type + "|" + data;
//        }
//
//        return new Job(id, finalPayload, priority, delay, deps);
//    }

    public static Job fromDagString(String jobStr) {
        String cleanedStr = jobStr.trim();
        String[] p = cleanedStr.split("\\|");

        // 1. Basic Validation
        if (p.length < 6) throw new IllegalArgumentException("Invalid DAG job format");

        String id = p[0].trim();
        String type = p[1].trim();
        String data = p[2].trim(); // This might be filename OR generic data (like EMAIL)

        String port = "";
        int prioIndex = 3;

        // Only look for a 7th column (Port) if it is a DEPLOY command
        if (type.equalsIgnoreCase("DEPLOY") && p.length == 7) {
            port = p[3].trim();
            prioIndex = 4; // Shift indices right
        }

        // Extract remaining numeric fields
        int priority = Integer.parseInt(p[prioIndex].trim());
        long delay = Long.parseLong(p[prioIndex + 1].trim());

        // Parse Dependencies
        String depRawStr = p[prioIndex + 2].replace("[", "").replace("]", "").trim();
        List<String> deps = (depRawStr.isEmpty()) ? null :
                java.util.Arrays.stream(depRawStr.split(","))
                        .map(String::trim).toList();

        // Construct Payload
        String finalPayload;
        if (type.equalsIgnoreCase("RUN") || type.equalsIgnoreCase("DEPLOY")) {
            // ONLY these types trigger File I/O and Base64 encoding
            finalPayload = constructFilePayload(type, data, port);
        } else {
            // For everything else (EMAIL, PDF_CONVERT), just pass the data as-is
            finalPayload = type + "|" + data;
        }

        return new Job(id, finalPayload, priority, delay, deps);
    }

    // Helper method for the File I/O logic
    private static String constructFilePayload(String type, String filename, String port) {
        try {
            java.io.File file = new java.io.File("perm_files" + java.io.File.separator + filename);
            String base64Content = "";

            if (file.exists()) {
                byte[] fileBytes = java.nio.file.Files.readAllBytes(file.toPath());
                base64Content = java.util.Base64.getEncoder().encodeToString(fileBytes);
            } else {
                System.err.println("[ERROR] Warning: File not found: " + filename);
                // Fallback: send without base64, though worker might fail
                return type + "|" + filename;
            }

            if (type.equalsIgnoreCase("RUN")) {
                return "RUN_PAYLOAD|" + filename + "|" + base64Content;
            } else { // DEPLOY
                return "DEPLOY_PAYLOAD|" + filename + "|" + base64Content + "|" + port;
            }
        } catch (Exception e) {
            System.err.println("[FAIL] Payload Error: " + e.getMessage());
            return type + "|" + filename;
        }
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
