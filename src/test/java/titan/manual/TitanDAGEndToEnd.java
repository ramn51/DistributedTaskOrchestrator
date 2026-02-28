/*
 * Copyright 2026 Ram Narayanan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
 */

package titan.manual;

import titan.network.RpcWorkerServer;
import titan.network.TitanProtocol;
import titan.scheduler.Scheduler;
import titan.scheduler.Job;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.Socket;

public class TitanDAGEndToEnd {
    private static Scheduler scheduler;

    public static void main(String[] args) throws Exception {
        scheduler = new Scheduler(9090);
        scheduler.start();

        // WORKER 1 (Port 8080)
        RpcWorkerServer worker1 = new RpcWorkerServer(8080, "localhost", 9090, "TEST", false);
        new Thread(() -> { try { worker1.start(); } catch (Exception e) {} }).start();

        // WORKER 2 (Port 8081)
        RpcWorkerServer worker2 = new RpcWorkerServer(8081, "localhost", 9090, "TEST", false);
        new Thread(() -> { try { worker2.start(); } catch (Exception e) {} }).start();

        System.out.println("Waiting for workers to register...");
        Thread.sleep(3000);

        // --- TESTS ---
        testSimpleSequence();
        testDiamondDag();
        testCascadingFailure();
        testSimpleAffinity();
        testComplexFanOutAffinity();

        // NEW TEST: Cycle Detection
        testCycleDetectionRejection();

        System.out.println("\n=== ALL VALIDATIONS COMPLETE ===");
        System.exit(0);
    }

    private static void testSimpleSequence() throws Exception {
        System.out.println("\n--- 1. Validating Simple Sequence (A -> B) ---");
        sendDag("S1_A|TEST|calc.py|2|0|[] ; S1_B|TEST|calc.py|1|0|[S1_A]");

        Thread.sleep(4000);

        assertStatus("DAG-S1_A", Job.Status.COMPLETED);
        assertStatus("DAG-S1_B", Job.Status.COMPLETED);
    }

    private static void testDiamondDag() throws Exception {
        System.out.println("\n--- 2. Validating Diamond DAG ---");
        sendDag("D_ROOT|TEST|calc.py|2|0|[] ; " +
                "D_LEFT|TEST|calc.py|1|0|[D_ROOT] ; " +
                "D_RIGHT|TEST|calc.py|1|0|[D_ROOT] ; " +
                "D_FINAL|TEST|calc.py|1|0|[D_LEFT,D_RIGHT]");

        Thread.sleep(6000);

        assertStatus("DAG-D_ROOT", Job.Status.COMPLETED);
        assertStatus("DAG-D_LEFT", Job.Status.COMPLETED);
        assertStatus("DAG-D_RIGHT", Job.Status.COMPLETED);
        assertStatus("DAG-D_FINAL", Job.Status.COMPLETED);
    }

    private static void testCascadingFailure() throws Exception {
        System.out.println("\n--- 3. Validating Cascading Failure ---");
        sendDag("F_PARENT|TEST|FAIL_THIS|2|0|[] ; " +
                "F_CHILD|TEST|calc.py|1|0|[F_PARENT] ; " +
                "F_GRAND|TEST|calc.py|1|0|[F_CHILD]");

        Thread.sleep(12000); // Retries take time

        assertStatus("DAG-F_PARENT", Job.Status.DEAD);
        assertStatus("DAG-F_CHILD", Job.Status.DEAD);
        assertStatus("DAG-F_GRAND", Job.Status.DEAD);
    }

    private static void testSimpleAffinity() throws Exception {
        System.out.println("\n--- 4. Validating Simple Affinity (Parent -> Child) ---");
        String dag = "AFF_PARENT|TEST|calc.py|2|0|[] ; " +
                "AFF_CHILD|TEST|calc.py|1|0|[AFF_PARENT]|AFFINITY";

        sendDag(dag);

        Thread.sleep(5000);

        assertStatus("DAG-AFF_PARENT", Job.Status.COMPLETED);
        assertStatus("DAG-AFF_CHILD", Job.Status.COMPLETED);
        assertAffinity("DAG-AFF_PARENT", "DAG-AFF_CHILD");
    }

    private static void testComplexFanOutAffinity() throws Exception {
        System.out.println("\n--- 5. Validating Complex Fan-Out Affinity ---");
        String dag =
                "ML_TRAIN|TEST|calc.py|5|0|[] ; " +
                        "ML_EVAL_A|TEST|calc.py|1|0|[ML_TRAIN]|AFFINITY ; " +
                        "ML_EVAL_B|TEST|calc.py|1|0|[ML_TRAIN]|AFFINITY";

        sendDag(dag);

        Thread.sleep(6000);

        assertStatus("DAG-ML_TRAIN", Job.Status.COMPLETED);
        assertStatus("DAG-ML_EVAL_A", Job.Status.COMPLETED);
        assertStatus("DAG-ML_EVAL_B", Job.Status.COMPLETED);

        assertAffinity("DAG-ML_TRAIN", "DAG-ML_EVAL_A");
        assertAffinity("DAG-ML_TRAIN", "DAG-ML_EVAL_B");
    }

    /**
     * NEW TEST: Validates Kahn's Algorithm implementation in SchedulerServer.
     * Submits a DAG with a 3-node cycle (A -> B -> C -> A) and asserts
     * that the Scheduler safely aborts the payload without polluting memory.
     */
    private static void testCycleDetectionRejection() throws Exception {
        System.out.println("\n--- 6. Validating Pre-Flight Cycle Detection (Kahn's Algorithm) ---");

        // C depends on B, B depends on A, A depends on C. (Deadlock)
        String cyclicDag = "CYC_A|TEST|calc.py|1|0|[CYC_C] ; " +
                "CYC_B|TEST|calc.py|1|0|[CYC_A] ; " +
                "CYC_C|TEST|calc.py|1|0|[CYC_B]";

        sendDag(cyclicDag);

        // Give the SchedulerServer a moment to parse and reject it
        Thread.sleep(1500);

        // If Kahn's algorithm works, the Master refuses to instantiate these jobs.
        // Therefore, the dagWaitingRoom should NOT contain them.
        boolean isSafelyRejected = !scheduler.getDAGWaitingRoom().containsKey("DAG-CYC_A");

        if (isSafelyRejected) {
            System.out.println("[OK] [PASS] Cyclic DAG was successfully detected and rejected.");
        } else {
            System.err.println("[FAIL] [FAIL] Cyclic DAG bypassed Kahn's Algorithm and polluted the waiting room!");
        }
    }

    // --- HELPERS (Keep exactly the same) ---

    private static void assertStatus(String id, Job.Status expected) throws InterruptedException {
        Job.Status actual = Job.Status.PENDING;
        for (int i = 0; i < 15; i++) {
            actual = scheduler.getJobStatus(id);
            if (actual == expected) break;
            Thread.sleep(500);
        }

        if (actual == expected) {
            System.out.println("[OK] [PASS] " + id + " is " + expected);
        } else {
            System.err.println("[FAIL] [FAIL] " + id + " expected " + expected + " but was " + actual);
        }
    }

    private static void assertAffinity(String parentId, String childId) {
        String jsonStats = scheduler.getSystemStatsJSON();
        String parentWorker = findWorkerForJob(jsonStats, parentId);
        String childWorker = findWorkerForJob(jsonStats, childId);

        if (parentWorker == null || childWorker == null) {
            System.err.println("[FAIL] Affinity Check: Could not find job history in JSON stats.");
            return;
        }

        if (parentWorker.equals(childWorker)) {
            System.out.println("[OK] [AFFINITY] " + childId + " followed " + parentId + " to Worker " + parentWorker);
        } else {
            System.err.println("[FAIL] [AFFINITY] Broken! Parent on " + parentWorker + " but Child on " + childWorker);
        }
    }

    private static String findWorkerForJob(String json, String jobId) {
        String[] workers = json.split("\"port\":");
        for (int i = 1; i < workers.length; i++) {
            String segment = workers[i];
            String port = segment.split(",")[0].trim();
            if (segment.contains("\"id\": \"" + jobId + "\"")) {
                return port;
            }
        }
        return null;
    }

    private static void sendDag(String dagPayload) {
        try (Socket s = new Socket("localhost", 9090);
             DataOutputStream out = new DataOutputStream(s.getOutputStream());
             DataInputStream in = new DataInputStream(s.getInputStream())
        ) {
            TitanProtocol.send(out, TitanProtocol.OP_SUBMIT_DAG, dagPayload);
            TitanProtocol.read(in);
        } catch (Exception e) { e.printStackTrace(); }
    }
}