package network;

import scheduler.Job;
import scheduler.Scheduler;
import scheduler.WorkerRegistry;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SchedulerServer {
    private final int port;
    private boolean isRunning = true;
    private final ExecutorService threadPool;
    Scheduler scheduler;
    private final ServerSocket serverSocket;

    private static final String PERM_FILES_DIR = "perm_files";

    public SchedulerServer(int port, Scheduler scheduler) throws IOException {
        this.port = port;
        threadPool = Executors.newCachedThreadPool();
        this.scheduler = scheduler;
        this.serverSocket = new ServerSocket(this.port);
    }

    public void start(){
        try(serverSocket){
            System.out.println("[OK] SchedulerServer Listening on port " + port);
            while(isRunning){
                try{
                    Socket clientSocket = serverSocket.accept();
                    System.out.println("Incoming connection from " + clientSocket.getInetAddress());
                    threadPool.submit(() -> clientHandler(clientSocket));
                } catch (IOException e){
                    e.printStackTrace();
                }
            }
        }catch(Exception e){
            e.printStackTrace();
        }
    }

    private String handleRegistration(Socket socket, String request){
            String[] parts = request.split("\\|\\|");
            String capability = (parts.length > 2) ? parts[2] : "GENERAL";
            int workerPort = Integer.parseInt(parts[1]);
            String host = socket.getInetAddress().getHostAddress();

            System.out.println("Registering Worker: " + host + " with " + capability);
            scheduler.registerWorker(host, workerPort, capability);
//            scheduler.getWorkerRegistry().addWorker(host, workerPort, capability);
            return ("REGISTERED");
    }

    public void clientHandler(Socket socket){
        try(socket;
            DataInputStream in = new DataInputStream(socket.getInputStream());
            DataOutputStream out = new DataOutputStream(socket.getOutputStream())
        ){

            String request = TitanProtocol.read(in);
            if(request == null)return;
            System.out.println("User Request: " + request);

            String response;
            if(request.startsWith("REGISTER")){
                response = handleRegistration(socket, request);
            } else{
                response = processCommand(request);
            }

            TitanProtocol.send(out, response);

        } catch (IOException e) {
            System.err.println("Error handling user: " + e.getMessage());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private String handleDeployRequest(String fileName, String port) {
        try {
            File file = new File(PERM_FILES_DIR + File.separator + fileName);
            if (!file.exists()) {
                return "ERROR: File not found in " + PERM_FILES_DIR;
            }

            byte[] fileBytes = Files.readAllBytes(file.toPath());
            String base64Content = Base64.getEncoder().encodeToString(fileBytes);

            Job job = new Job("TEMP_PAYLOAD", 1, 0);
            String internalId = job.getId();

            // If it's a Worker, we include the port in the ID for easy matching later
            String taggedId = (fileName.equalsIgnoreCase("Worker.jar"))
                    ? "WRK-" + port + "-" + internalId
                    : "TSK-" + internalId;

            // 3. Update the Job with the tagged ID and final payload
            job.setId(taggedId);

            // 2. Construct a Payload that contains EVERYTHING the worker needs
            // Format: DEPLOY_PAYLOAD|filename|base64data
            String payload = "DEPLOY_PAYLOAD|" + fileName + "|" + base64Content + "|" + port;
            job.setPayload(payload);
            scheduler.submitJob(job);

            System.out.println("[DEPLOY] Job queued for file: " + fileName);
            return "DEPLOY_QUEUED";

        } catch (IOException e) {
            e.printStackTrace();
            return "ERROR: Server File IO issue";
        }
    }


    private String handleRunScript(String fileName){
        try {


            File file = new File(PERM_FILES_DIR + File.separator + fileName);
            if (!file.exists()) {
                return "ERROR: File not found in " + PERM_FILES_DIR;
            }

            byte[] fileBytes = Files.readAllBytes(file.toPath());
            String base64Content = Base64.getEncoder().encodeToString(fileBytes);


            if (base64Content == null) return "ERROR: File not found";

            String payload = "RUN_PAYLOAD|" + fileName + "|" + base64Content;
            // Payload: RUN_PAYLOAD|filename|base64
            Job job = new Job(payload, 1, 0);
            scheduler.submitJob(job);
            return "JOB_QUEUED";
        } catch (IOException e) {
            e.printStackTrace();
            return "ERROR: Server File IO issue";
        }
    }

    private void parseAndSubmitDAG(String request){
        String [] jobs = request.split(";");
        for(String jobDef: jobs){
            try {
                Job job = Job.fromDagString(jobDef.trim());
                System.out.println("[INFO] [PARSER] Created Job: " + job.getId());
                scheduler.submitJob(job);
            } catch (Exception e) {
                System.err.println("[FAIL] Failed to parse DAG job: " + jobDef + " Error: " + e.getMessage());
            }
        }
    }


    private String processCommand(String request){
        if (request.startsWith("DEPLOY")) {
            String[] parts = request.split("\\|");
            if (parts.length < 2) return "ERROR: Missing filename";

            String fileName = parts[1];
            // Capture the port if provided, otherwise null/empty
            String port = (parts.length > 2) ? parts[2] : "";

            return handleDeployRequest(fileName, port);
        }

        if (request.startsWith("RUN")) {
            // Format: EXECUTE RUN_SCRIPT|filename
            String[] parts = request.split("\\|");
            if (parts.length < 2) return "ERROR: Missing filename";
            String filename = parts[1];

            return handleRunScript(filename);
        }

        // Add this block inside processCommand method
        if (request.startsWith("UNREGISTER_SERVICE")) {
            String[] parts = request.split("\\|");
            if (parts.length > 1) {
                String serviceId = parts[1];
                // Remove the service from the map
                scheduler.getLiveServiceMap().remove(serviceId);
                System.out.println("[INFO] Cleaned up service record for: " + serviceId);
                return "ACK_UNREGISTERED";
            }
        }

        if (request.equalsIgnoreCase("STATS_JSON")) {
            System.out.println("[INFO] Generating JSON Stats...");
            return scheduler.getSystemStatsJSON();
        }

        if (request.equalsIgnoreCase("CLEAN_STATS")) {
            scheduler.getLiveServiceMap().clear();
            return "Stats Map Cleared. Run STATS again to see fresh state.";
        }

        if (request.startsWith("STOP")) {
            String[] parts = request.split("\\|");
            if (parts.length < 2) return "ERROR: Missing Service ID";

            // Just call the clean public API
            return scheduler.stopRemoteService(parts[1]);
        }

        if (request.equalsIgnoreCase("STATS")) {
            return scheduler.getSystemStats();
        }

        if (request.startsWith("SUBMIT_DAG")){
            parseAndSubmitDAG(request.substring(10).trim());
            return "DAG_ACCEPTED";
        }
        else if(request.startsWith("SUBMIT")){
            String jobPayload = request.substring(7).trim();
            scheduler.submitJob(jobPayload);
            return "JOB_ACCEPTED";
        }
        else if (request.contains("SUSPEND")) {
            return "SUSPEND_JOB";
        } else{
            return "UNKNOWN_COMMAND";
        }
    }

    public void stop(){
        isRunning = false;
        threadPool.shutdown();

        try{
            if(serverSocket != null && !serverSocket.isClosed())
                serverSocket.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
