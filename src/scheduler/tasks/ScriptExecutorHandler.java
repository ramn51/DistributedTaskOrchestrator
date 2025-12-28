package scheduler.tasks;

import network.RpcWorkerServer;
import scheduler.TaskHandler;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeUnit;

public class ScriptExecutorHandler implements TaskHandler {
    private static final String WORKSPACE_DIR = "titan_workspace";
    private final RpcWorkerServer parentServer;
    public ScriptExecutorHandler(RpcWorkerServer parentServer) {
        this.parentServer = parentServer;
    }

    @Override
    public String execute(String payload) {
        // Payload comes from RpcWorkerServer as: "filename.py|JOB-123"
        String[] parts = payload.split("\\|");
        String filename = parts[0];

        String jobId = (parts.length > 1) ? parts[1] : "script_" + System.currentTimeMillis();

        System.out.println("[INFO] [ScriptExecutor] Running: " + filename + " (ID: " + jobId + ")");
        File scriptFile = new File(WORKSPACE_DIR + File.separator + filename);

        if (!scriptFile.exists()) {
            return "ERROR: Script file not found: " + filename;
        }

        try {
            //Determine Interpreter
            ProcessBuilder pb;
            if (filename.endsWith(".py")) {
                pb = new ProcessBuilder("python", scriptFile.getAbsolutePath());
            } else if (filename.endsWith(".sh")) {
                pb = new ProcessBuilder("/bin/bash", scriptFile.getAbsolutePath());
            } else {
                // Assume executable binary
                pb = new ProcessBuilder(scriptFile.getAbsolutePath());
            }

            // Combine Errors with Output
            pb.redirectErrorStream(true);

            // 3. Start Process
            Process process = pb.start();

            StringBuilder finalOutput = new StringBuilder();

            Thread streamer = new Thread(() -> {
                File logFile = new File(WORKSPACE_DIR, jobId + ".log");
               try(BufferedReader bufferedReader = new BufferedReader(new InputStreamReader(process.getInputStream()));
                   BufferedWriter fileWriter = new BufferedWriter(new FileWriter(logFile, true))){

                       String line;

                       while ((line = bufferedReader.readLine()) != null) {
                           parentServer.streamLogToMaster(jobId, line);

                           fileWriter.write(line);
                           fileWriter.newLine();
                           fileWriter.flush();

                           synchronized (finalOutput) {
                               finalOutput.append(line).append("\n");
                           }
                       }
               }catch (IOException e) { /* Stream ended */ }
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
