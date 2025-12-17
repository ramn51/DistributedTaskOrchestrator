package tests;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import network.TitanProtocol;


public class TestServer {
    public static void main(String[] args){
        ExecutorService executorService = Executors.newFixedThreadPool(2);
        executorService.submit(()->{
            try (ServerSocket server = new ServerSocket(9999)) {
                System.out.println("Listening on 9999");

                try (Socket socket = server.accept()) {
                    // Read the request
                    DataInputStream in = new DataInputStream(socket.getInputStream());
                    String msg = TitanProtocol.read(in);
                    System.out.println("Message from client" + msg);

                    DataOutputStream out = new DataOutputStream(socket.getOutputStream());
                    TitanProtocol.send(out, "Echo: " + msg + "Someof");
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        });

        try { Thread.sleep(100); } catch (Exception e) {}



        try{
            Socket socket = new Socket("localhost", 9999);
            DataOutputStream out = new DataOutputStream(socket.getOutputStream());
            TitanProtocol.send(out, "Testing TCP!");

            DataInputStream in = new DataInputStream(socket.getInputStream());
            String response = TitanProtocol.read(in);
            System.out.println("[Client] Got back: " + response);

        } catch (Exception e){
            e.printStackTrace();
        }

        executorService.shutdown();
    }
}
