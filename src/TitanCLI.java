import network.TitanProtocol;
import java.io.*;
import java.net.Socket;
import java.util.Scanner;

public class TitanCLI {
    private final String host;
    private final int port;
    private final Scanner scanner;

    public TitanCLI(String host, int port) {
        this.host = host;
        this.port = port;
        this.scanner = new Scanner(System.in);
    }

    public void start() {
        System.out.println("==========================================");
        System.out.println("    [INFO] TITAN DISTRIBUTED ORCHESTRATOR    ");
        System.out.println("==========================================");
        System.out.println("Connected to: " + host + ":" + port);
        System.out.println("Commands: stats, submit <skill> <data>, dag <raw_dag>, exit");

        while (true) {
            System.out.print("\ntitan> ");
            String input = scanner.nextLine().trim();

            if (input.equalsIgnoreCase("exit")) break;
            if (input.isEmpty()) continue;

            handleCommand(input);
        }
    }

    private void handleCommand(String input) {
        String protocolMsg;

        if (input.equalsIgnoreCase("stats")) {
            protocolMsg = "STATS";
        } else if (input.startsWith("submit ")) {
            // Converts 'submit TEST data' -> 'SUBMIT TEST|data|1|0'
            String[] parts = input.substring(7).split(" ", 2);
            if (parts.length < 2) {
                System.out.println("[FAIL] Usage: submit <skill> <data>");
                return;
            }
            protocolMsg = "SUBMIT " + parts[0] + "|" + parts[1] + "|1|0";
        } else if (input.startsWith("dag ")) {
            // Passes raw DAG string
            protocolMsg = "SUBMIT_DAG " + input.substring(4);
        } else {
            // Direct protocol access for advanced users
            protocolMsg = input;
        }

        String response = sendAndReceive(protocolMsg);
        System.out.println("[INFO] Server Response:\n" + response);
    }

    private String sendAndReceive(String msg) {
        try (Socket socket = new Socket(host, port);
             DataOutputStream out = new DataOutputStream(socket.getOutputStream());
             DataInputStream in = new DataInputStream(socket.getInputStream())) {

            TitanProtocol.send(out, msg);
            return TitanProtocol.read(in);

        } catch (IOException e) {
            return "[FAIL] Error: Could not reach Scheduler at " + host + ":" + port;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public static void main(String[] args) {
        new TitanCLI("localhost", 9090).start();
    }
}