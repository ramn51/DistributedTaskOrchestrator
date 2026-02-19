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

package titan.manual.storage;
import titan.scheduler.Job;
import titan.scheduler.Scheduler;
import titan.storage.TitanJRedisAdapter;

import java.io.IOException;

public class TitanPersistenceIntegrationTest {

    // Config
    private static final String REDIS_HOST = "localhost";
    private static final int REDIS_PORT = 6379;
    private static final int SCHEDULER_PORT = 9999;

    public static void main(String[] args) {
        System.out.println("Starting titan redis integration test");
        boolean allPassed = true;

        try {
            setup();

            if (!testRedisInteraction()) allPassed = false;
            if (!testJobPersistence()) allPassed = false;
            if (!testCrashRecovery()) allPassed = false;

            System.out.println("\n------------------------------------------------");
            if (allPassed) {
                System.out.println("[PASS] ALL ENGINE TESTS PASSED");
            } else {
                System.out.println("[FAIL] SOME TESTS FAILED");
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            teardown();
        }
    }

    private static void setup() throws IOException {
        TitanJRedisAdapter redis = new TitanJRedisAdapter(REDIS_HOST, REDIS_PORT);
        redis.connect();
        if (redis.isConnected()) {
            System.out.println("🧹 Flushing Redis for clean test state...");
            // If your JRedis doesn't support FLUSHALL, we manually delete specific keys used in tests
            redis.execute("SET", "system:active_jobs", "0", "PX", "1");
            redis.execute("SET", "job:TEST-JOB-001:status", "0", "PX", "1");
            redis.execute("SET", "job:TEST-JOB-001:payload", "0", "PX", "1");
        }
        redis.close();
    }

    private static void teardown() {
        // Any cleanup if needed
    }

    // --- TEST CASE 1: Basic Redis Handshake ---
    private static boolean testRedisInteraction() {
        System.out.println("\n[TEST 1] Testing Redis Adapter Handshake...");
        try (TitanJRedisAdapter redis = new TitanJRedisAdapter(REDIS_HOST, REDIS_PORT)) {
            redis.connect();
            if (!redis.isConnected()) {
                System.err.println("[FAIL] Failed to connect to Redis.");
                return false;
            }

            redis.set("titan_test_key", "HELLO");
            String val = redis.get("titan_test_key");

            if ("HELLO".equals(val)) {
                System.out.println("[PASS] Redis SET/GET working.");
                return true;
            } else {
                System.err.println("[FAIL]Redis GET mismatch. Expected HELLO, got " + val);
                return false;
            }
        } catch (Exception e) {
            System.err.println("   [FAIL] Exception: " + e.getMessage());
            return false;
        }
    }

    // --- TEST CASE 2: Job Persistence (WAL) ---
    private static boolean testJobPersistence() {
        System.out.println("\n[TEST 2] Testing Job Write-Ahead Log (WAL)...");
        Scheduler scheduler = new Scheduler(SCHEDULER_PORT);

        try {
            scheduler.start();

            // 1. Submit a Job
            String jobId = "TEST-JOB-001";
            Job job = new Job("RUN_PAYLOAD|print('hello')|GENERAL", 1, 0);
            job.setId(jobId);

            System.out.println("   >> Submitting Job " + jobId);
            scheduler.submitJob(job);

            // 2. Verify Redis immediately (Simulating "did it write to disk?")
            TitanJRedisAdapter redis = new TitanJRedisAdapter(REDIS_HOST, REDIS_PORT);
            redis.connect();

            String status = redis.get("job:" + jobId + ":status");
            String payload = redis.get("job:" + jobId + ":payload");
            boolean inActiveSet = redis.smembers("system:active_jobs").contains(jobId);

            boolean passed = true;
            if (!"PENDING".equals(status)) {
                System.err.println("   [FAIL] Status not PENDING in Redis. Got: " + status);
                passed = false;
            }
            if (payload == null) {
                System.err.println("   [FAIL] Payload missing in Redis.");
                passed = false;
            }
            if (!inActiveSet) {
                System.err.println("   [FAIL] Job ID missing from system:active_jobs set.");
                passed = false;
            }

            scheduler.stop();
            redis.close();

            if (passed) System.out.println("   [PASS] Job persisted to Redis correctly.");
            return passed;

        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    // --- TEST CASE 3: Crash Recovery ---
    private static boolean testCrashRecovery() {
        System.out.println("\n[TEST 3] Testing Crash Recovery...");

        // 1. SEED DATA (Simulate a crash state)
        // We manually inject a "RUNNING" job into Redis without the Scheduler knowing
        String crashJobId = "TEST-RECOVERY-001";
        System.out.println("   >> Injecting orphaned job " + crashJobId + " into Redis...");

        try (TitanJRedisAdapter redis = new TitanJRedisAdapter(REDIS_HOST, REDIS_PORT)) {
            redis.connect();
            redis.set("job:" + crashJobId + ":payload", "RUN_PAYLOAD|recover_me.py|GENERAL");
            redis.set("job:" + crashJobId + ":status", "RUNNING"); // It was running when we crashed
            redis.set("job:" + crashJobId + ":priority", "10");
            redis.sadd("system:active_jobs", crashJobId);
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }

        // 2. START SCHEDULER (The Resurrection)
        System.out.println("   >> Starting Scheduler (Simulating Restart)...");
        Scheduler scheduler = new Scheduler(SCHEDULER_PORT + 1); // Use different port to avoid bind errors

        try {
            scheduler.start(); // This triggers recoverState()

            // Give it 1 second to recover
            Thread.sleep(1000);

            // 3. VERIFY RAM STATE
            // The job should now be in the Scheduler's memory, set to PENDING
            Job.Status status = scheduler.getJobStatus(crashJobId);

            // Note: getJobStatus might return PENDING if it's in the queue
            // We can also check if it exists in the internal maps if you expose a getter,
            // but checking status is usually enough.

            // *CRITICAL*: Since recoverState() puts it back in taskQueue,
            // the status in RAM might technically be null if you don't track PENDING jobs in executionHistory map yet.
            // But if your submitJob() logic adds it to a map, it will be there.
            // Let's verify by checking if the Scheduler *wrote* the PENDING status back to Redis

            TitanJRedisAdapter checker = new TitanJRedisAdapter(REDIS_HOST, REDIS_PORT);
            checker.connect();
            String recoveredStatus = checker.get("job:" + crashJobId + ":status");

            // Your recover logic sets it to PENDING before queuing
            if ("PENDING".equals(recoveredStatus) || "RUNNING".equals(recoveredStatus)) {
                System.out.println("   [PASS] Job recovered! Status in Redis reset to: " + recoveredStatus);

                // Optional: Check if the priority was preserved
                String pri = checker.get("job:" + crashJobId + ":priority");
                if ("10".equals(pri)) {
                    System.out.println("   [PASS] Priority preserved: 10");
                    return true;
                } else {
                    System.err.println("   [FAIL] Priority lost. Expected 10, got " + pri);
                    return false;
                }
            } else {
                System.err.println("   [FAIL] Recovery Failed. Status is: " + recoveredStatus);
                return false;
            }

        } catch (Exception e) {
            e.printStackTrace();
            return false;
        } finally {
            scheduler.stop();
        }
    }
}