package scheduler;


import network.RpcClient;
import network.SchedulerServer;

import java.io.IOException;
import java.util.List;
import java.util.Queue;
import java.util.concurrent.*;

public class Scheduler {
    private final WorkerRegistry workerRegistry;
    private final RpcClient schedulerClient;
    private final Queue<String> taskQueue;
    private SchedulerServer schedulerServer;

    private final ScheduledExecutorService heartBeatExecutor;
    private final ExecutorService dispatchExecutor;
    private final ExecutorService serverExecutor;
    private volatile boolean isRunning = true;
    private int port;

    public Scheduler(int port){
        workerRegistry = new WorkerRegistry();
        schedulerClient = new RpcClient(workerRegistry);
        this.taskQueue = new ConcurrentLinkedDeque<>();
        this.port = port;
        this.heartBeatExecutor = Executors.newSingleThreadScheduledExecutor();
        this.dispatchExecutor = Executors.newSingleThreadExecutor();
        this.serverExecutor = Executors.newSingleThreadExecutor();
        try{
            this.schedulerServer = new SchedulerServer(port, this);
        } catch (IOException e){
            throw new RuntimeException("Failed to start Scheduler Server", e);
        }
    }

    public void start(){
        System.out.println("Scheduler Core starting at port " + this.port);

//        new Thread(() -> schedulerServer.start()).start();
        serverExecutor.submit(() -> schedulerServer.start());

        heartBeatExecutor.scheduleAtFixedRate(
                this::checkHeartBeat,
                5, 10, TimeUnit.SECONDS
        );

        dispatchExecutor.submit(this::runDispatchLoop);

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
            } else{
                workerRegistry.updateLastSeen(worker.host(), worker.port());
            }
        }
    }

    public void submitJob(String jobPayload) {
        System.out.println("📥 Scheduler received job: " + jobPayload);
        taskQueue.add(jobPayload);
    }

    private void runDispatchLoop() {
        System.out.println("Running Dispatch Loop");
        while (isRunning) {
            try{
                if(taskQueue.isEmpty()){
                    Thread.sleep(1000);
                    continue;
                }
                String jobPayload = taskQueue.peek();
                String[] parts = jobPayload.split("\\|", 2);
                String reqTaskSkill = parts[0];

                List<Worker> availableWorkers = workerRegistry.getWorkersByCapability(reqTaskSkill);
                if(availableWorkers.isEmpty()){
                    System.out.println("No available workers");
                    Thread.sleep(2000);
                    continue;
                }

                // Replace this with Round robin
                Worker selectedWorker = availableWorkers.get(ThreadLocalRandom.current().nextInt(availableWorkers.size()));
                System.out.println("🚀 Dispatching " + jobPayload + " to Worker " + selectedWorker.port());

                String response = schedulerClient.sendRequest(selectedWorker.host(), selectedWorker.port(),
                                                            "EXECUTE " + jobPayload);

                if (response != null && !response.startsWith("ERROR") && !response.startsWith("JOB_FAILED")) {
                    System.out.println("✅ Job Finished: " + response);
                    taskQueue.poll();
                } else {
                    System.err.println("❌ Job Failed on Worker " + selectedWorker.port() + ": " + response);
                    // Simple Retry Logic: Leave it in the queue, wait a bit
                    Thread.sleep(1000);
                }

            } catch (Exception e){
                e.printStackTrace();
            }
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
