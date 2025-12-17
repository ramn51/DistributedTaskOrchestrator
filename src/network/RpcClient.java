package network;

import scheduler.WorkerRegistry;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.Socket;

public class RpcClient {
    WorkerRegistry workerRegistry;
//    public RpcClient(){}
    public RpcClient(WorkerRegistry workerRegistry){
        this.workerRegistry = workerRegistry;
    }

    public String sendRequest(String host, int port, String payload){
        try(Socket socket = new Socket(host, port)){
            DataOutputStream out = new DataOutputStream(socket.getOutputStream());
            socket.setSoTimeout(10000); // If i dont get response within 3 seconds I timeout (detecting failed jobs)
            TitanProtocol.send(out, payload);

            DataInputStream in = new DataInputStream(socket.getInputStream());
            String response = TitanProtocol.read(in);

            return response;
        } catch (Exception e){
            System.err.println("RPC Failed to " + host + ": " + e.getMessage());
            return null;
        }
    }

}
