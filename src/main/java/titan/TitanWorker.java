package titan;

import titan.network.RpcWorkerServer;

public class TitanWorker {
    public static void main(String[] args) {
        int myPort = 8080;
        String masterHost = "localhost";
        int masterPort = 9090;
        String capability = "GENERAL";

        // Argument Parsing: [Port] [MasterIP] [MasterPort] [Capability]
        try {
            if (args.length > 0) myPort = Integer.parseInt(args[0]);
            if (args.length > 1) masterHost = args[1];
            if (args.length > 2) masterPort = Integer.parseInt(args[2]);
            if (args.length > 3) capability = args[3];
        } catch (NumberFormatException e) {
            System.err.println("❌ Invalid argument format. Usage: java -jar Worker.jar <Port> <MasterIP> <MasterPort>");
            return;
        }

        System.out.println("   ** Starting Titan Worker Node**");
        System.out.println("   Local Port:  " + myPort);
        System.out.println("   Master:      " + masterHost + ":" + masterPort);
        System.out.println("   Capability:  " + capability);

        try {
            RpcWorkerServer worker = new RpcWorkerServer(myPort, masterHost, masterPort, capability);
            worker.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}