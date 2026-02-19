/*
 * Copyright 2026 Ram Narayanan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
 */
package titan.storage;
import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * A synchronous adapter to connect Titan to RedisJava.
 * Implements the RESP (Redis Serialization Protocol) for sending commands.
 */
public class TitanJRedisAdapter implements AutoCloseable {
    private final String host;
    private final int port;
    private Socket socket;
    private OutputStream out;
    private BufferedInputStream in;
    private boolean isConnected;

    public TitanJRedisAdapter(String host, int port) {
        this.host = host;
        this.port = port;
        isConnected = false;
    }

    public void connect() throws IOException {

        if (host == null || host.isEmpty() || port <= 0) {
            System.out.println("[INFO] No Redis config found. Running in IN-MEMORY mode (No Persistence).");
            this.isConnected = false;
            return;
        }


        try {
            this.socket = new Socket(host, port);
            this.socket.setTcpNoDelay(true); // For low latency
            this.out = socket.getOutputStream();
            this.in = new BufferedInputStream(socket.getInputStream());
            this.isConnected = true;
            System.out.println("[INFO][SUCCESS] Connected to Redis for Persistence.");
        } catch (IOException e) {
            System.err.println("[FATAL][FAILED] Could not connect to Redis (" + e.getMessage() + "). Running in IN-MEMORY mode.");
            this.isConnected = false;
        }
    }

    public boolean isConnected(){
        return this.isConnected;
    }

    public synchronized Object execute(String... args) throws IOException {
        sendCommand(args);
        return readResponse();
    }

    public String get(String key) throws IOException {
        if (!isConnected) return null;
        try {
            return (String) execute("GET", key);
        } catch (IOException e) {
            this.isConnected = false;
            return null;
        }
    }

    public String set(String key, String value) throws IOException {
        if (!isConnected) {
            return null;
        }
        try {
            return (String) execute("SET", key, value);
        } catch (IOException e) {
            System.err.println("[INFO][FAILED] Redis Write Failed: " + e.getMessage());
            this.isConnected = false;
            return null;
        }
    }

    public long sadd(String key, String member) throws IOException {
        if (!isConnected) return 0;
        try {
            Object res = execute("SADD", key, member);
            if (res instanceof Long) return (Long) res;
            return 0;
        } catch (IOException e) {
            System.err.println("[INFO][FAILED] Redis SADD failed: " + e.getMessage());
            this.isConnected = false;
            return 0;
        }
    }

    @SuppressWarnings("unchecked")
    public Set<String> smembers(String key) throws IOException {
        if (!isConnected) return Collections.emptySet();

        try {
            Object res = execute("SMEMBERS", key);
            if (res instanceof List) {
                return new HashSet<>((List<String>) res);
            }
        } catch (IOException e) {
            System.err.println("[INFO][FAILED] Redis SMEMBERS failed: " + e.getMessage());
            this.isConnected = false;
        }

        return Collections.emptySet();
    }

    public long srem(String key, String member) {
        if (!isConnected) return 0;
        try {
            Object res = execute("SREM", key, member);
            if (res instanceof Long) return (Long) res;
            return 0;
        } catch (IOException e) {
            System.err.println("[INFO][FAILED] Redis SREM failed: " + e.getMessage());
            this.isConnected = false;
            return 0;
        }
    }


    private void sendCommand(String... args) throws IOException {
        StringBuilder sb = new StringBuilder();
        sb.append("*").append(args.length).append("\r\n");
        for (String arg : args) {
            sb.append("$").append(arg.length()).append("\r\n");
            sb.append(arg).append("\r\n");
        }
        out.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        out.flush();
    }

    private Object readResponse() throws IOException {
        int b = in.read();
        if (b == -1) throw new IOException("Connection closed by RedisJava");

        char type = (char) b;
        switch (type) {
            case '+': // Simple String (e.g., +OK)
                return readLine();
            case '-': // Error
                throw new IOException("RedisJava Error: " + readLine());
            case ':': // Integer
                return Long.parseLong(readLine());
            case '$': // Bulk String
                return readBulkString();
            case '*': // Array
                return readArray();
            default:
                throw new IOException("Unknown RESP type: " + type);
        }
    }

    private String readLine() throws IOException {
        StringBuilder sb = new StringBuilder();
        int b;
        while ((b = in.read()) != -1) {
            if (b == '\r') {
                in.read();
                break;
            }
            sb.append((char) b);
        }
        return sb.toString();
    }

    private String readBulkString() throws IOException {
        String lenStr = readLine();
        int len = Integer.parseInt(lenStr);
        if (len == -1) return null; // Null Bulk String

        byte[] data = new byte[len];
        int totalRead = 0;
        while (totalRead < len) {
            int read = in.read(data, totalRead, len - totalRead);
            if (read == -1) throw new IOException("Unexpected end of stream");
            totalRead += read;
        }
        in.read(); // consume \r
        in.read(); // consume \n
        return new String(data, StandardCharsets.UTF_8);
    }

    private List<Object> readArray() throws IOException {
        String countStr = readLine();
        int count = Integer.parseInt(countStr);
        if (count == -1) return null;

        List<Object> list = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            list.add(readResponse());
        }
        return list;
    }

    @Override
    public void close() throws IOException {
        if (socket != null && !socket.isClosed()) {
            socket.close();
        }
    }
}