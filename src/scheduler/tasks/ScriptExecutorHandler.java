package scheduler.tasks;

import network.RpcWorkerServer;
import scheduler.TaskHandler;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

public class ScriptExecutorHandler implements TaskHandler {
    private static final String WORKSPACE_DIR = "titan_workspace";
    private final RpcWorkerServer parentServer;

    private final File rootWorkspace;
    private final File sharedWorkspace;

    public ScriptExecutorHandler(RpcWorkerServer parentServer) {
        this.parentServer = parentServer;

        this.rootWorkspace = new File(WORKSPACE_DIR);
        if (!rootWorkspace.exists()) {
            boolean created = rootWorkspace.mkdirs();
            if(created) System.out.println("[INIT] Created Root Workspace: " + rootWorkspace.getAbsolutePath());
        }

        this.sharedWorkspace = new File(rootWorkspace, "shared");
        if (!sharedWorkspace.exists()) {
            sharedWorkspace.mkdirs();
            System.out.println("[INIT] Created Shared DAG Workspace: " + sharedWorkspace.getAbsolutePath());
        }
    }

    @Override
    public String execute(String payload) {
        // Payload comes from RpcWorkerServer as: "filename.py|JOB-123"
        String[] parts = payload.split("\\|");
        String filename = parts[0];
        System.out.println("GIVEN PAYLOAD TO SCRIPT EXECUTOR " + payload);

//        String jobId = (parts.length > 1) ? parts[1] : "script_" + System.currentTimeMillis();
        String jobId = filename;

        // Handle RUN_PAYLOAD prefix if present
        if (filename.equals("RUN_PAYLOAD")) {
            if (parts.length > 1) filename = parts[1];
        }

        // NEW PARSER: The Job ID is now the LAST part of the payload
        if (parts.length > 1) {
            String lastPart = parts[parts.length - 1];
            if (!lastPart.equals(filename) && !lastPart.equals("RUN_PAYLOAD")) {
                jobId = lastPart;
            }
        }

        System.out.println("[INFO] [ScriptExecutor] Filename: " + filename + " | Context ID: " + jobId);

        System.out.println("[INFO] [ScriptExecutor] Running: " + filename + " (ID: " + jobId + ")");
//        File scriptFile = new File(WORKSPACE_DIR + File.separator + filename);
        File scriptFile = new File(rootWorkspace, filename);

        if (!scriptFile.exists()) {
            return "ERROR: Script file not found: " + filename;
        }

        try {

            File executionDir;
            // 3. Selection Logic (No redundant mkdirs for Shared)
            if (jobId.startsWith("DAG-")) {
                // Use the pre-calculated shared folder
                executionDir = this.sharedWorkspace;
            } else {
                // ISOLATED: This MUST be created on the run, as it is unique to this job
                executionDir = new File(rootWorkspace, jobId);
                if (!executionDir.exists()) executionDir.mkdirs();
            }

            //Determine Interpreter
            ProcessBuilder pb;
            if (filename.endsWith(".py")) {
                pb = new ProcessBuilder("python", "-u" ,scriptFile.getAbsolutePath());
            } else if (filename.endsWith(".sh")) {
                pb = new ProcessBuilder("/bin/bash", scriptFile.getAbsolutePath());
            } else {
                // Assume executable binary
                pb = new ProcessBuilder(scriptFile.getAbsolutePath());
            }

            pb.directory(executionDir);
            // Combine Errors with Output
            pb.redirectErrorStream(true);

            System.out.println("[INFO] Context: " + executionDir.getName());

            // 3. Start Process
            Process process = pb.start();

            final String finalJobId = jobId;

            StringBuilder finalOutput = new StringBuilder();

            Thread streamer = new Thread(() -> {
                File logFile = new File(executionDir, finalJobId + ".log");
                System.out.println("[DEBUG] Writing logs to: " + logFile.getAbsolutePath());
                try(BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                   BufferedWriter fileWriter = new BufferedWriter(new FileWriter(logFile, true))){

                       String line;

                       while ((line = bufferedReader.readLine()) != null) {
                           parentServer.streamLogToMaster(finalJobId, line);

                           fileWriter.write(line);
                           fileWriter.newLine();
                           fileWriter.flush();

//                           System.out.println("[STREAM] " + line);

                           synchronized (finalOutput) {
                               finalOutput.append(line).append("\n");
                           }
                       }
               }catch (IOException e) { e.printStackTrace();}
            });

            streamer.start();

            // 4. Wait for completion
            boolean finished = process.waitFor(60, TimeUnit.SECONDS);
            streamer.join(); // this ensures we capture the last line of the o/p.

            if (!finished) {
                process.destroy();
                return "ERROR: Script timed out (60s limit)";
            }

            // 5. Read Output (Byte-oriented for TitanProtocol compatibility)
//            byte[] outputBytes = process.getInputStream().readAllBytes();
//            String output = new String(outputBytes, StandardCharsets.UTF_8).trim();
            int exitCode = process.exitValue();
            // Format: COMPLETED|ExitCode|OutputContent
            return "COMPLETED|" + exitCode + "|" + finalOutput.toString().trim();

        } catch (Exception e) {
            e.printStackTrace();
            return "ERROR: Execution failed - " + e.getMessage();
        }
    }
}
