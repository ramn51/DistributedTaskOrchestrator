package network;

import scheduler.Scheduler;
import scheduler.WorkerRegistry;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SchedulerServer {
    private final int port;
    private boolean isRunning = true;
    private final ExecutorService threadPool;
    Scheduler scheduler;
    private final ServerSocket serverSocket;

    public SchedulerServer(int port, Scheduler scheduler) throws IOException {
        this.port = port;
        threadPool = Executors.newCachedThreadPool();
        this.scheduler = scheduler;
        this.serverSocket = new ServerSocket(this.port);
    }

    public void start(){
        try(serverSocket){
            System.out.println("✅ SchedulerServer Listening on port " + port);
            while(isRunning){
                try{
                    Socket clientSocket = serverSocket.accept();
                    System.out.println("⚡ Incoming connection from " + clientSocket.getInetAddress());
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

            System.out.println("➕ Registering Worker: " + host + " with " + capability);
            scheduler.getWorkerRegistry().addWorker(host, workerPort, capability);
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

    private String processCommand(String request){
        if(request.startsWith("SUBMIT")){
            String jobPayload = request.substring(7).trim();
            scheduler.submitJob(jobPayload);
            return "JOB_ACCEPTED";
        } else if (request.contains("SUSPEND")) {
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
