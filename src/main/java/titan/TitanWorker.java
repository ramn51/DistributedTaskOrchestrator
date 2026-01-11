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

package titan;

import titan.network.RpcWorkerServer;

public class TitanWorker {
    public static void main(String[] args) {
        int myPort = 8080;
        String masterHost = "localhost";
        int masterPort = 9090;
        String capability = "GENERAL";
        boolean isPermanent = false; // auto-scaler can descale this node (kill it in default false)

        // Argument Parsing: [Port] [MasterIP] [MasterPort] [Capability]
        try {
            if (args.length > 0) myPort = Integer.parseInt(args[0]);
            if (args.length > 1) masterHost = args[1];
            if (args.length > 2) masterPort = Integer.parseInt(args[2]);
            if (args.length > 3 && !args[3].isEmpty()){
                String arg3 = args[3];
                // This is to validate if the given arg is for capability or for isPermanent
                if (arg3.equalsIgnoreCase("true") || arg3.equalsIgnoreCase("false")) {
                    System.out.println("Detected boolean in Capability slot. Assuming you meant 'isPermanent'" +
                                        "Setting capability to default GENERAL");
                    capability = "GENERAL";
                    isPermanent = Boolean.parseBoolean(arg3);
                } else {
                    capability = arg3;

                    // Only check args[4] if args[3] was NOT a boolean shift
                    if (args.length > 4) {
                        isPermanent = Boolean.parseBoolean(args[4]);
                    }
                }
            }
        } catch (NumberFormatException e) {
            System.err.println("[ERROR] Invalid argument format. Usage: java -jar Worker.jar <Port> <MasterIP> <MasterPort>");
            return;
        }

        System.out.println("   ** Starting Titan Worker Node**");
        System.out.println("   Local Port:  " + myPort);
        System.out.println("   Master:      " + masterHost + ":" + masterPort);
        System.out.println("   Capability:  " + capability);
        System.out.println("   Mode:        " + (isPermanent ? "PERMANENT (Protected)" : "EPHEMERAL (Auto-Scaleable)"));

        try {
            RpcWorkerServer worker = new RpcWorkerServer(myPort, masterHost, masterPort, capability, isPermanent);
            worker.start();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}