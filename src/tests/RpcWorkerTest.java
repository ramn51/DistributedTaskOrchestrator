package tests;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import network.RpcClient;
import network.RpcWorkerServer;
import scheduler.WorkerRegistry;

public class RpcWorkerTest {
    public static void main(String [] args) throws InterruptedException {
        int TEST_PORT = 9999;
        String TEST_CAPABILITY = "PDF";

        ExecutorService executorService = Executors.newFixedThreadPool(2);
        System.out.println("[TEST] Starting Worker Server on port " + TEST_PORT + "...");
        String schedulerHost = "localhost";
        int schedulerPort = 8080;

        RpcWorkerServer workerServer = new RpcWorkerServer(TEST_PORT, schedulerHost, schedulerPort, TEST_CAPABILITY);

        Future<?> future = executorService.submit(() -> {
            try {
                workerServer.start();
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        });

        Thread.sleep(1000);

        WorkerRegistry workerRegistry = new WorkerRegistry();
        RpcClient rpcClient = new RpcClient(workerRegistry);
        System.out.println("[TEST] Sending PING...");
        String response1 = rpcClient.sendRequest("localhost", TEST_PORT, "PING");

        if ("PONG".equals(response1)) {
            System.out.println("✅ PING Test PASSED. Response: " + response1);
        } else {
            System.err.println("❌ PING Test FAILED. Response: " + response1);
        }

        System.out.println("[TEST] Sending EXECUTE...");
        String response2 = rpcClient.sendRequest("localhost", TEST_PORT, "EXECUTE Job_123");

        if ("EXECUTED".equals(response2)) {
            System.out.println("✅ EXECUTE Test PASSED. Response: " + response2);
        } else {
            System.err.println("❌ EXECUTE Test FAILED. Response: " + response2);
        }

        // --- STEP 5: Cleanup ---
        System.out.println("[TEST] Stopping Server...");

        executorService.shutdown();
        System.exit(0);
    }
}
