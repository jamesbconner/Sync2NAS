# 📜 SFTP Test Philosophy

## Purpose

The `SFTPService` class is a critical integration layer between the Sync2NAS system and external SFTP servers.  
Its responsibilities include **connection management**, **file and directory listing**, **recursive downloading**, and **retry logic for network failures**.

Testing this class requires a deliberate strategy:
- To **verify** the functional logic (filtering, listing, downloading)
- While **avoiding fragile coupling** to external services (like real SFTP servers or Paramiko internals)

---

## Core Testing Principles

### 🧹 1. **Mock low-level network operations only, not the business logic**

- **We mock `client.listdir_attr`, `client.get`, and connection methods**.
- **We do not mock `list_remote_dir`, `download_dir`, etc.**  
  Instead, we exercise them fully, ensuring filtering, recursion, and retries work.

This ensures tests validate **our service’s logic**, not Paramiko’s implementation.

---

### 🔄 2. **Retry Logic is Active**

- We allow the `@retry_sftp_operation` decorator to stay active in tests.
- We patch the `reconnect` method (where needed) so retries do not trigger actual network calls.
- Retry behavior can be separately tested with forced exceptions if needed.

This ensures **production behavior matches test behavior** exactly.

---

### 🛡️ 3. **Protect Production Code from Test Artifacts**

- No "test-only" flags, "injected mocks," or "alternate connection modes" exist inside `SFTPService`.
- All testing setup is isolated to the test files using `pytest-mock`.

This preserves the **purity and maintainability of production code**.

---

### 🔍 4. **Functional Testing: Focus on Outcomes, Not Mock Structures**

Rather than asserting that mocks were called a certain way, the tests **assert the results**:
- Which files are listed
- Which files are downloaded
- How many entries exist
- Whether errors propagate appropriately

This ensures tests verify **the behavior users care about**, not implementation trivia.

---

## Practical Notes

| Aspect | Approach |
|:---|:---|
| **SFTP Listing** | Mock `listdir_attr` to simulate remote directory structures |
| **SFTP Downloads** | Mock `get()` to avoid actual file transfers |
| **Reconnects** | Patch `reconnect()` to a no-op in retry tests |
| **Decorators** | Decorators remain active; we never bypass them artificially |
| **Recursion** | Recursive downloads and listings are simulated with multiple return values |

---

## 🚀 Why This Matters

By following these principles, Sync2NAS gains:
- **Robust test coverage** of SFTP workflows
- **Confidence that retries, downloads, and filtering work together**
- **Isolation** from network flakiness, speed, and environment configuration

## Philosophy Summary:  
✅ **Tests verify what matters, stay fast, and don’t warp production code.**

# 🔗 Related Links
- [Main README](../README.md)