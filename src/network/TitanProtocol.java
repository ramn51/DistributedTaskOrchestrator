package network;

import java.io.*;
import java.nio.charset.StandardCharsets;

public class TitanProtocol {

    public static void send(DataOutputStream out, String payload) throws IOException {
        byte[] payloadBytes = payload.getBytes(StandardCharsets.UTF_8);
        int len = payloadBytes.length;
        out.writeInt(len);
        out.write(payloadBytes);
        out.flush();
        System.out.println("[TitanProtocol] Sent: " + payload);
    }

    public static String read(DataInputStream in) throws Exception {
        int len = in.readInt();
        if(len > 1024 * 1024 * 10){
            throw new Exception("Packet too large: " + len);
        }
        byte[] buffer = new byte[len];
        in.readFully(buffer);
        return new String(buffer, StandardCharsets.UTF_8);
    }

    public static void main(String[] args){
        try {
            // 1. Simulate the "Network" using a Byte Array
            ByteArrayOutputStream virtualNetwork = new ByteArrayOutputStream();
            DataOutputStream out = new DataOutputStream(virtualNetwork);

            // 2. SEND: Write a message to our fake network
            String originalMessage = "Hello, Titan Orchestrator!";
            System.out.println("Sending: " + originalMessage);
            TitanProtocol.send(out, originalMessage);

            // 3. RECEIVE: Read it back from the byte array
            // We convert the output stream -> input stream
            ByteArrayInputStream inputData = new ByteArrayInputStream(virtualNetwork.toByteArray());
            DataInputStream in = new DataInputStream(inputData);

            String receivedMessage = TitanProtocol.read(in);
            System.out.println("Received: " + receivedMessage);

            // 4. Verify
            if (originalMessage.equals(receivedMessage)) {
                System.out.println("[OK] TEST PASSED: Protocols match!");
            } else {
                System.out.println("[FAIL] TEST FAILED: Messages differ.");
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        System.out.println("Hello");
    }
}
