# Automotive ECU Software Safety & Coding Guidelines

**Standard Reference:** AUTO-SEC-SPEC-2026-V1  
**Target Architecture:** ARM Cortex-R52 / Infineon AURIX TC39x  
**Classification:** ISO 26262 ASIL-B / ASIL-D Compliant  

---

## 1. Dynamic Memory Allocation (MISRA C:2012 Rule 21.3 / Dir 4.12)
In safety-critical automotive Electronic Control Units (ECUs), dynamic memory allocation using `malloc()`, `calloc()`, `realloc()`, `free()`, or C++ `new`/`delete` is **STRICTLY PROHIBITED** during operational control loops.
- **Rationale:** Prevents nondeterministic execution timing, memory fragmentation, and memory leaks.
- **Standard Practice:** All buffers, queues, and message envelopes must be allocated statically at compile-time with fixed maximum bounds.

---

## 2. CAN Bus Message Handling & Payload Verification (AUTOSAR SecOC)
All CAN frame unpacking routines must validate that the Data Length Code (DLC) does not exceed the destination buffer capacity:
- Prior to executing `memcpy()` or byte transfers, code must assert that `message->dlc <= sizeof(dest_buffer)` and `message->dlc <= 8`.
- Unchecked memory copies constitute a Critical Buffer Overflow vulnerability (CWE-120).

---

## 3. Cryptographic Keys and Diagnostic Secret Protection (CWE-798 / ISO 21434)
Diagnostic authentication keys, challenge-response seeds, and encryption keys must **NEVER** be stored as cleartext strings or `#define` macros in firmware source code.
- **Requirement:** Keys must be stored inside a Hardware Security Module (HSM) or Secure Hardware Extension (SHE).
- Source code must interface exclusively via AUTOSAR Crypto Service Manager (CSM) APIs.

---

## 4. Null Pointer Verification (CWE-476 / MISRA C Rule 11.8)
Pointers to hardware sensor peripherals, actuators, or memory mapped registers must be checked for non-null pointer validity (`ptr != nullptr`) prior to dereferencing.
- Unchecked dereferences result in CPU Hardware Fault Exceptions (MemManage / HardFault) causing ECU reset.
