package scheduler;


import network.RpcClient;
import network.SchedulerServer;

import java.io.IOException;
import java.util.ArrayDeque;
import java.util.List;
import java.util.Queue;
import java.util.concurrent.*;
import java.util.concurrent.DelayQueue;

public class Scheduler {
    private final WorkerRegistry workerRegistry;
    private final RpcClient schedulerClient;
    private final Queue<Job> taskQueue;
    private final BlockingQueue<ScheduledJob> waitingRoom;
    private final Queue<Job> deadLetterQueue;
    private final SchedulerServer schedulerServer;

    private final ScheduledExecutorService heartBeatExecutor;
    private final ExecutorService dispatchExecutor;
    private final ExecutorService serverExecutor;
    private volatile boolean isRunning = true;
    private int port;

    public Scheduler(int port){
        workerRegistry = new WorkerRegistry();
        schedulerClient = new RpcClient(workerRegistry);
//        this.taskQueue = new ConcurrentLinkedDeque<>();
        this.taskQueue = new PriorityBlockingQueue<>();
        this.deadLetterQueue = new ConcurrentLinkedDeque<>();
        this.waitingRoom = new DelayQueue<>();

        this.port = port;
        this.heartBeatExecutor = Executors.newSingleThreadScheduledExecutor();
        this.dispatchExecutor = Executors.newSingleThreadExecutor();
        this.serverExecutor = Executors.newSingleThreadExecutor();
        try{
            this.schedulerServer = new SchedulerServer(port, this);
        } catch (IOException e){
            throw new RuntimeException("Failed to start Scheduler Server", e);
        }

        Thread clockWatcher = new Thread(() -> {
            System.out.println("Clock Watcher Started...");
            while (isRunning) {
                try {
                    ScheduledJob readyJob = waitingRoom.take();
                    System.out.println("Time's up! Moving Job " + readyJob.getJob().getId() + " to Active Queue.");
                    taskQueue.add(readyJob.getJob());

                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
        });
        clockWatcher.setDaemon(true);
        clockWatcher.start();
    }

    public void start(){
        System.out.println("Scheduler Core starting at port " + this.port);

//        new Thread(() -> schedulerServer.start()).start();
        serverExecutor.submit(() -> {
            try {
                schedulerServer.start();
            } catch (Exception e) {
                System.err.println("❌ Scheduler Server crashed: " + e.getMessage());
            }
        });

        heartBeatExecutor.scheduleAtFixedRate(
                this::checkHeartBeat,
                5, 10, TimeUnit.SECONDS
        );

        dispatchExecutor.submit(() -> {
            try {
                runDispatchLoop();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt(); // Restore interrupt status
                System.out.println("🛑 Dispatch Loop stopped.");
            } catch (Throwable t) {
                // Catches RuntimeException, NoClassDefFoundError, OutOfMemoryError, etc.
                System.err.println("CRITICAL: Dispatch Loop Died Unexpectedly!");
                t.printStackTrace();
            }
        });
    }

    public WorkerRegistry getWorkerRegistry(){
        return workerRegistry;
    }

    public void checkHeartBeat(){
        System.out.println("Sending Heartbeat");
        for(Worker worker: workerRegistry.getWorkers()){
            String result = schedulerClient.sendRequest(worker.host(), worker.port(), "PING");
            if(result  == null){
                workerRegistry.markWorkerDead(worker.host(), worker.port());
            } else if(result.startsWith("PONG")){
                worker.updateLastSeen();
                String[] parts = result.split("\\|");
                if (parts.length > 1) {
                    int load = Integer.parseInt(parts[1]);
                    worker.setCurrentLoad(load);
                    if(load > 0){
                        System.out.println("Worker " + worker.port() + "Has load" + worker.getCurrentLoad());
                    }
                }
                workerRegistry.updateLastSeen(worker.host(), worker.port());
            }
        }
    }

    public void submitJob(Job job){
        long delay = job.getScheduledTime() - System.currentTimeMillis();
        if(delay <=0){
            // Run the job now (Add to the queue, dispatcher will do the polling and execution)
            System.out.println(" ** Queueing Job: " + job.getId());
            taskQueue.add(job);
        } else{
            System.out.println("⏳ Job Delayed: " + job.getId() + " for " + delay + "ms");
            waitingRoom.add(new ScheduledJob(job));
        }
    }

    public void submitJob(String jobPayload) {
        System.out.println("** Scheduler received job: " + jobPayload);
        String[] parts = jobPayload.split("\\|");
        String data = parts.length > 1 ? parts[0] + "|" + parts[1] : jobPayload;
        int priority = parts.length > 2 ? Integer.parseInt(parts[2]) : 1;
        long delay = parts.length > 3 ? Long.parseLong(parts[3]) : 0;

        submitJob(new Job(data, priority, delay));
    }

    private void runDispatchLoop() throws InterruptedException {
        System.out.println("Running Dispatch Loop");
        while (isRunning) {

                if(taskQueue.isEmpty()){
                    Thread.sleep(1000);
                    continue;
                }
                Job job = taskQueue.poll();
                job.setStatus(Job.Status.RUNNING);
                System.out.println(" Job Processing: " + job);

                String[] parts = job.getPayload().split("\\|", 2);
                String reqTaskSkill = parts[0];

                List<Worker> availableWorkers = workerRegistry.getWorkersByCapability(reqTaskSkill);
                if(availableWorkers.isEmpty()){
                    System.out.println("No available workers");
                    job.setStatus(Job.Status.PENDING);
                    taskQueue.add(job);
                    Thread.sleep(2000);
                    continue;
                }

                // Get the least loaded worker
                Worker bestWorker = null;
                int minLoad = Integer.MAX_VALUE;
                for(Worker worker: availableWorkers){
                    if(worker.isSaturated())
                        continue;

                    if(worker.getCurrentLoad() < minLoad){
                        minLoad = worker.getCurrentLoad();
                        bestWorker = worker;
                    }
                }

                if(bestWorker == null){
                    System.out.println("All workers SATURATED. Re-queueing job.");
                    job.setStatus(Job.Status.PENDING);
                    taskQueue.add(job);
                    Thread.sleep(1000);
                    continue;
                }

                Worker selectedWorker = bestWorker;
//                Worker selectedWorker = availableWorkers.get(ThreadLocalRandom.current().nextInt(availableWorkers.size()));
                System.out.println("🚀 Dispatching " + job.getPayload() + " to Worker " + selectedWorker.port());

                try{
                    String response = schedulerClient.sendRequest(selectedWorker.host(), selectedWorker.port(),
                            "EXECUTE " + job.getPayload());

                    if (response != null && !response.startsWith("ERROR") && !response.startsWith("JOB_FAILED")) {
                        System.out.println("✅ Job Finished: " + response);
                        job.setStatus(Job.Status.COMPLETED);
                    } else {
                        System.err.println("❌ Job Failed on Worker " + selectedWorker.port() + ": " + response);
                        throw new RuntimeException("Worker returned error: " + response);
                    }
                } catch (Exception e){
                    handleJobFailure(job);
                }

            }
        }

    private void handleJobFailure(Job job) {
        job.incrementRetry();
        if(job.getRetryCount() > 3) {
            job.setStatus(Job.Status.DEAD);
            System.err.println("Job Moved to DLQ (Max Retries): " + job);
            this.deadLetterQueue.offer(job);
        } else{
            job.setStatus(Job.Status.FAILED);
            System.err.println("Job Failed. Retrying... (" + job.getRetryCount() + "/3)");
            job.setStatus(Job.Status.PENDING);
            taskQueue.offer(job);
        }
    }


    public void stop(){
        if(isRunning){
            isRunning = false;

            if (schedulerServer != null) schedulerServer.stop();

            serverExecutor.shutdownNow();
            heartBeatExecutor.shutdownNow();
            dispatchExecutor.shutdownNow();
        }
    }
}
