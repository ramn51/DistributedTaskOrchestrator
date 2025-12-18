import network.RpcWorkerServer;

public class TitanWorker {
    public static void main(String[] args) {
        // Start Worker on port 8080, connect to Scheduler on 9090
        // Skill: TEST
        try {
            RpcWorkerServer worker = new RpcWorkerServer(8080, "localhost", 9090, "TEST");
            worker.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}