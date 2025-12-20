package scheduler.tasks;

import network.RpcWorkerServer;
import network.TitanProtocol;
import scheduler.TaskHandler;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class ServiceHandler implements TaskHandler {
    private static final Map<String, Process> runningServices = new ConcurrentHashMap<>();
    private static final String WORKSPACE_DIR = "./titan_workspace/";
    private final String operation;

    private final RpcWorkerServer parentServer;

    public ServiceHandler(String op, RpcWorkerServer parentServer){
        this.operation = op;
        this.parentServer = parentServer;
    }

    @Override
    public String execute(String payload) {
        String [] parts = payload.split("\\|");

        if(operation.equals("START")){
            String fileName = parts[0];
            String serviceId = (parts.length > 1) ? parts[1] : "svc_" + System.currentTimeMillis();
            String portToUse = (parts.length > 2) ? parts[2] : "8085";

            return startProcess(fileName, serviceId, portToUse);
        } else {
            String idToKill = (parts.length > 1) ? parts[1] : parts[0];
            return stopProcess(idToKill);
        }
    }

    private String startProcess(String fileName, String serviceId, String port){
        // Payload: "filename|service_id"
        File scriptFile = new File(WORKSPACE_DIR, fileName);

        if(!scriptFile.exists()){
            return "ERROR: File not found at " + scriptFile.getAbsolutePath();
        }

        if (fileName.endsWith(".jar")) {
            String javaHome = System.getProperty("java.home");
            String javaBin = javaHome + File.separator + "bin" + File.separator + "java";
            if (System.getProperty("os.name").toLowerCase().contains("win")) {
                javaBin += ".exe";
            }

            System.out.println("JAVA RUNTIME ::::" + javaBin);
            // To run a jar: java -jar <path>
            return launchDetachedProcess(serviceId, javaBin, "-jar", scriptFile.getAbsolutePath(), port);
        } else if (fileName.endsWith(".py")) {
            return launchDetachedProcess(serviceId, "python", scriptFile.getAbsolutePath());
        } else {
            // Default to trying to execute it directly (e.g. binaries or .sh)
            return launchDetachedProcess(serviceId, scriptFile.getAbsolutePath());
        }
    }

    private String launchDetachedProcess(String serviceId, String... command) {
        if (runningServices.containsKey(serviceId)) {
            return "SERVICE_ALREADY_RUNNING: " + serviceId;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder(command);

            // 2. Separate Logs (Crucial for debugging background jobs)
            File logFile = new File(WORKSPACE_DIR, serviceId + ".log");
            pb.redirectOutput(logFile);
            pb.redirectError(logFile);

            // 3. START (Async/Detached)
            Process process = pb.start();

            // 4. Register in Memory Map
            runningServices.put(serviceId, process);

            // 5. Clean up Map when process dies
            process.onExit().thenRun(() -> {
                runningServices.remove(serviceId);
                System.out.println("[INFO] Service Stopped: " + serviceId);
                parentServer.notifyMasterOfServiceStop(serviceId);
            });

            return "DEPLOYED_SUCCESS | ID: " + serviceId + " | PID: " + process.pid();

        } catch (IOException e) {
            e.printStackTrace();
            return "LAUNCH_ERROR: " + e.getMessage();
        }
    }

    private String stopProcess(String serviceId){
        Process p = runningServices.get(serviceId);
            if(p!=null){
                p.destroy();
                runningServices.remove(serviceId);
                return "STOPPED: " + serviceId;
            } else{
                return "UNKNOWN_SERVICE: " + serviceId;
            }
    }
}
