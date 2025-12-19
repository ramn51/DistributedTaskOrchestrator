import network.RpcWorkerServer;

public class TitanWorker {
    public static void main(String[] args) {
        int myPort = (args.length > 0) ? Integer.parseInt(args[0]) : 8080;
        try {
            // Change "TEST" to "GENERAL"
            RpcWorkerServer worker = new RpcWorkerServer(myPort, "localhost", 9090, "GENERAL");
            worker.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}