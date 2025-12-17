-----

# ⚡ Titan: Distributed Task Orchestrator

**Titan** is a high-performance, distributed job scheduler and workflow orchestrator. It is designed to manage complex task lifecycles across a cluster of workers with a focus on reliability, priority, and resource efficiency.

> **Status:** Phase 5 Complete (Smart Resource Allocation & Scheduling)

## 🏗 System Architecture

### 1\. The Scheduler (The Brain)

* **Dual-Queue Engine:** \* **Waiting Room (`DelayQueue`):** Holds future/scheduled jobs with zero CPU overhead until their execution time.
    * **Active Queue (`PriorityBlockingQueue`):** Manages ready-to-run jobs, ensuring high-priority (VIP) tasks jump to the front of the line.
* **Smart Dispatcher:** Uses a **Least-Connections** algorithm. It queries worker health via heartbeats and routes tasks to the node with the lowest current load.
* **Resilience Controller:** Implements a 3-strike retry policy, a **Dead Letter Queue (DLQ)** for poison-pill tasks, and network timeout handling to detect "zombie" workers.

### 2\. The Worker (The Limbs)

* **Resource Guarding:** Enforces a `FixedThreadPool` limit (e.g., 4 concurrent tasks). If the worker is at capacity, it enters a `SATURATED` state and notifies the scheduler.
* **Atomic Load Tracking:** Uses `AtomicInteger` to track real-time task count, reporting this via a `PONG|LOAD|MAX` handshake.

### 3\. The Protocol (The Language)

* **TitanProtocol:** A custom, length-prefixed binary protocol over TCP.
* **Commands:** `REGISTER`, `SUBMIT`, `EXECUTE`, `PING/PONG`, `JOB_COMPLETE`.

-----

## ✅ Core Capabilities

| Feature | Implementation Detail |
| :--- | :--- |
| **Fault Tolerance** | Automatic retries on worker crash; timeout detection. |
| **Priority** | 3-level priority (Low, Normal, High) with "line-cutting" logic. |
| **Scheduling** | Cron-like delay support via `DelayQueue`. |
| **Load Balancing** | Smart "Least-Loaded" worker selection (Resource-Aware). |
| **Discovery** | Dynamic worker registration; capability-based routing. |

-----

## 🚀 Quick Start

1.  **Start Scheduler:** `java scheduler.Scheduler 9090`
2.  **Start Worker:** `java network.RpcWorkerServer 8080 localhost 9090 PDF_CONVERT`
3.  **Submit Task:** `SUBMIT PDF_CONVERT|my_file.pdf|2|5000` (Skill | Data | Priority | Delay)

-----

## 📂 Project Structure

```text
src/
├── network/
│   ├── TitanProtocol.java       # Binary framing logic
│   ├── RpcClient.java           # Scheduler's communication tool (with Timeouts)
│   ├── RpcWorkerServer.java     # Worker implementation (Fixed Pool & Load Tracking)
│   └── SchedulerServer.java     # Job ingestion server
├── scheduler/
│   ├── Job.java                 # FSM-based Task object (Comparable)
│   ├── ScheduledJob.java        # DelayQueue wrapper
│   ├── Worker.java              # Mutable worker state (Load & Health)
│   ├── Scheduler.java           # The core "Brain" and Dispatch Loop
│   └── WorkerRegistry.java      # Dynamic inventory of the cluster
```

### Phase 6: Workflow Orchestration (DAGs)
Focus: Task Dependencies.

[ ] Dependency Management: Support for Directed Acyclic Graphs (DAGs). "Task B starts only after Task A succeeds."

[ ] Data Passing: Implementation of a shared "Context" or "Blob Store" to pass outputs from one worker to the next.

### Phase 7: Persistence & Reliability
Focus: Data Integrity.

[ ] SQLite/Journaling: Log every job state change to disk to ensure 0% data loss during Scheduler restarts.

[ ] Reconciliation Loop: A startup process to recover "Running" jobs that were interrupted by a crash.

### Phase 8: Cluster Observability
Focus: Monitoring.

[ ] Admin Dashboard: A lightweight CLI or Web UI to view real-time worker load, queue depth, and DLQ status.

[ ] Centralized Logging: Aggregate worker logs at the Scheduler level for easier debugging.

-----