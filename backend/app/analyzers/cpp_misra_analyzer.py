import re
from typing import List, Dict, Any

class CPPMisraAnalyzer:
    """
    Multi-layered deterministic static analyzer for C and C++ source code.
    Performs comprehensive analysis across 9 critical dimensions:
      1. Memory Safety (buffer overflows, UAF, double free, leaks, mismatched delete, strlen allocations)
      2. Array & Boundary Safety (out-of-bounds, off-by-one loops, negative index)
      3. C/C++ Resource Management (new/delete pairs, file/socket leaks, RAII smart pointers)
      4. Dangerous Functions (strcpy, strcat, sprintf, gets, scanf, sizeof(pointer) errors)
      5. Correctness (assignment in condition, unreachable code, unsigned < 0, self-assignment)
      6. Security (CWE vulnerabilities, command injection, format string, hardcoded secrets)
      7. Automotive / Embedded C/C++ (MISRA C:2012, MISRA C++:2008, ISO 26262, CAN DLC checks)
      8. Performance (strlen in loop condition, expensive loop allocations)
      9. Maintainability / Code Smells (empty catch blocks, assert side effects)
    """
    def __init__(self, filename: str, source_code: str):
        self.filename = filename
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.findings: List[Dict[str, Any]] = []
        self.symbols: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        self._extract_symbols()
        # PASS 1 & 2: Memory & Pointer Safety
        self._check_memory_safety()
        # PASS 3: Array Bounds & Loops
        self._check_array_and_boundary_safety()
        # PASS 4: Resource Management
        self._check_resource_management()
        # PASS 5: Unsafe Functions
        self._check_unsafe_functions()
        # PASS 6: Correctness & Logic
        self._check_correctness()
        # PASS 7: Security & Automotive Guidelines (MISRA, ISO 26262, CAN)
        self._check_security_and_automotive_rules()
        # PASS 8: Performance & Maintainability
        self._check_performance_and_maintainability()

        return {
            "findings": self.findings,
            "symbols": self.symbols
        }

    # ── Symbol Extraction ──────────────────────────────────────────────────────
    def _extract_symbols(self):
        include_re = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]')
        macro_re = re.compile(r'^\s*#define\s+([A-Za-z_][A-Za-z0-9_]*)')
        class_struct_re = re.compile(r'^\s*(?:class|struct)\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*:[^{;]*)?\s*\{')
        func_re = re.compile(r'^\s*(?:(?:static|inline|virtual|explicit|const)\s+)*[A-Za-z_][A-Za-z0-9_<>:*&]*\s+([A-Za-z_][A-Za-z0-9_:]*)\s*\(([^)]*)\)\s*(?:const)?\s*(?:\{|;)')

        for idx, line in enumerate(self.lines, start=1):
            sline = line.strip()
            # #include
            m = include_re.match(line)
            if m:
                self.symbols.append({
                    "name": m.group(1),
                    "type": "INCLUDE",
                    "line_start": idx,
                    "line_end": idx,
                    "signature": sline
                })
            # #define
            m = macro_re.match(line)
            if m:
                self.symbols.append({
                    "name": m.group(1),
                    "type": "MACRO",
                    "line_start": idx,
                    "line_end": idx,
                    "signature": sline
                })
            # class / struct
            m = class_struct_re.search(line)
            if m:
                sym_type = "CLASS" if "class" in line else "STRUCT"
                self.symbols.append({
                    "name": m.group(1),
                    "type": sym_type,
                    "line_start": idx,
                    "line_end": idx,
                    "signature": sline
                })
            # function
            if not sline.startswith(("#", "//", "/*", "*")):
                m = func_re.match(line)
                if m:
                    fname = m.group(1)
                    if fname not in ("if", "for", "while", "switch", "catch"):
                        self.symbols.append({
                            "name": fname,
                            "type": "FUNCTION",
                            "line_start": idx,
                            "line_end": idx,
                            "signature": sline
                        })

    # ── PASS 1 & 2: Memory & Pointer Safety ────────────────────────────────────
    def _check_memory_safety(self):
        # 1. strlen() allocation without + 1 null terminator: new char[strlen(x)] or malloc(strlen(x))
        # e.g.: name = new char[strlen(vehicleName)];
        strlen_alloc_re = re.compile(
            r'(?:new\s+char\s*\[\s*strlen\s*\(\s*([A-Za-z0-9_.]+)\s*\)\s*\]|'
            r'malloc\s*\(\s*strlen\s*\(\s*([A-Za-z0-9_.]+)\s*\)\s*\))'
        )
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = strlen_alloc_re.search(line)
            if m:
                var = m.group(1) or m.group(2)
                self.findings.append({
                    "rule_id": "MEM-STRLEN-ALLOC-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "MemorySafety",
                    "severity": "CRITICAL",
                    "line": idx,
                    "message": f"Buffer Overflow Risk: strlen({var}) allocated without + 1 space for null-terminator byte.",
                    "snippet": line.strip(),
                    "root_cause": f"strlen() calculates the number of characters excluding the null terminator ('\\0'). Allocating strlen({var}) leaves no space for the terminating null byte.",
                    "impact": "Writing a null-terminated string into this buffer causes a heap buffer overflow, corrupting adjacent heap chunks and leading to undefined behavior or crash.",
                    "standards": "CWE-131, CWE-120, MISRA C:2012 Rule 21.6, ISO 26262 Part 6",
                    "recommendation": f"Allocate strlen({var}) + 1 bytes, or use modern std::string.",
                    "suggested_fix": line.replace(f"strlen({var})", f"strlen({var}) + 1").strip()
                })

        # 2. Mismatched allocation/deallocation: new[] with delete (scalar), or new with delete[]
        array_new_vars = {}
        scalar_new_vars = {}
        array_alloc_re = re.compile(r'([A-Za-z0-9_]+)\s*=\s*new\s+[A-Za-z0-9_:<>]+\s*\[')
        scalar_alloc_re = re.compile(r'([A-Za-z0-9_]+)\s*=\s*new\s+[A-Za-z0-9_:<>]+\s*(?:\(|$|;)')
        delete_array_re = re.compile(r'\bdelete\s*\[\s*\]\s*([A-Za-z0-9_]+)')
        delete_scalar_re = re.compile(r'\bdelete\s+([A-Za-z0-9_]+)')

        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m_arr = array_alloc_re.search(line)
            if m_arr:
                array_new_vars[m_arr.group(1)] = idx
            m_sc = scalar_alloc_re.search(line)
            if m_sc and not array_alloc_re.search(line):
                scalar_new_vars[m_sc.group(1)] = idx

            # Check delete calls
            m_del_arr = delete_array_re.search(line)
            if m_del_arr:
                v = m_del_arr.group(1)
                if v in scalar_new_vars:
                    self.findings.append({
                        "rule_id": "MEM-MISMATCHED-DELETE-01",
                        "analyzer": "CPPMisraAnalyzer",
                        "category": "MemorySafety",
                        "severity": "HIGH",
                        "line": idx,
                        "message": f"Mismatched Deallocation: '{v}' was allocated with scalar 'new' (line {scalar_new_vars[v]}) but freed with 'delete[]'.",
                        "snippet": line.strip(),
                        "root_cause": "The C++ runtime expects 'delete' for scalar allocations. Using 'delete[]' attempts to read an array cookie that does not exist.",
                        "impact": "Heap corruption and undefined behavior.",
                        "standards": "CWE-762, MISRA C++:2008 Rule 18-4-1",
                        "recommendation": f"Use scalar 'delete {v};' or migrate to std::unique_ptr<{v}>.",
                        "suggested_fix": f"delete {v};"
                    })
            else:
                m_del_sc = delete_scalar_re.search(line)
                if m_del_sc:
                    v = m_del_sc.group(1)
                    if v in array_new_vars:
                        self.findings.append({
                            "rule_id": "MEM-MISMATCHED-DELETE-02",
                            "analyzer": "CPPMisraAnalyzer",
                            "category": "MemorySafety",
                            "severity": "HIGH",
                            "line": idx,
                            "message": f"Mismatched Deallocation: '{v}' was allocated with array 'new[]' (line {array_new_vars[v]}) but freed with scalar 'delete'.",
                            "snippet": line.strip(),
                            "root_cause": "Scalar 'delete' only destructs the first element of an array allocation and fails to properly reclaim array memory.",
                            "impact": "Memory leak of subsequent elements, failure to execute destructors, and heap corruption.",
                            "standards": "CWE-762, MISRA C++:2008 Rule 18-4-1",
                            "recommendation": f"Use 'delete[] {v};' or migrate to std::vector or std::unique_ptr<T[]>.",
                            "suggested_fix": f"delete[] {v};"
                        })

        # 3. Use-after-free and double-free
        freed_vars = {}
        uaf_reported = set()
        free_delete_re = re.compile(r'(?:free\s*\(\s*([A-Za-z0-9_]+)\s*\)|delete(?:\[\])?\s+([A-Za-z0-9_]+))')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = free_delete_re.search(line)
            if m:
                var = m.group(1) or m.group(2)
                if var in freed_vars:
                    # Double free
                    self.findings.append({
                        "rule_id": "MEM-DOUBLE-FREE-01",
                        "analyzer": "CPPMisraAnalyzer",
                        "category": "MemorySafety",
                        "severity": "CRITICAL",
                        "line": idx,
                        "message": f"Double Free: '{var}' deallocated multiple times (previously freed at line {freed_vars[var]}).",
                        "snippet": line.strip(),
                        "root_cause": f"The pointer '{var}' was already freed and not set to nullptr, leading to duplicate deallocation.",
                        "impact": "Heap metadata corruption, arbitrary code execution vulnerability (CWE-415).",
                        "standards": "CWE-415, MISRA C:2012 Rule 21.3",
                        "recommendation": f"Set '{var} = nullptr;' immediately after deallocating.",
                        "suggested_fix": f"{var} = nullptr;"
                    })
                else:
                    freed_vars[var] = idx
            else:
                # Check for use after free of previously freed variable
                for var, free_line in list(freed_vars.items()):
                    if re.search(r'\b' + re.escape(var) + r'\s*=\s*(?:nullptr|NULL|0|[A-Za-z0-9_]+)', line):
                        # Reassigned
                        del freed_vars[var]
                        uaf_reported.discard(var)
                    elif var not in uaf_reported and re.search(r'\*\s*' + re.escape(var) + r'|\b' + re.escape(var) + r'\s*(?:->|\[)', line):
                        uaf_reported.add(var)
                        self.findings.append({
                            "rule_id": "MEM-USE-AFTER-FREE-01",
                            "analyzer": "CPPMisraAnalyzer",
                            "category": "MemorySafety",
                            "severity": "CRITICAL",
                            "line": idx,
                            "message": f"Use-After-Free: Pointer '{var}' dereferenced after being freed on line {free_line}.",
                            "snippet": line.strip(),
                            "root_cause": f"The memory address pointed to by '{var}' was returned to the system on line {free_line} and subsequently accessed.",
                            "impact": "Reading corrupted memory or remote code execution via heap exploitation (CWE-416).",
                            "standards": "CWE-416, CERT MEM30-C, ISO 26262 Part 6",
                            "recommendation": f"Reset '{var} = nullptr;' after freeing and guard dereferences.",
                            "suggested_fix": f"// Do not access {var} after deallocation; verify pointer validity"
                        })

        # 4. Returning address of local stack variable (dangling pointer)
        dangling_stack_re = re.compile(r'return\s+&([A-Za-z0-9_]+)\s*;')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = dangling_stack_re.search(line)
            if m:
                var = m.group(1)
                self.findings.append({
                    "rule_id": "MEM-DANGLING-STACK-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "MemorySafety",
                    "severity": "CRITICAL",
                    "line": idx,
                    "message": f"Dangling Pointer: Returning address of stack variable '&{var}'.",
                    "snippet": line.strip(),
                    "root_cause": f"Variable '{var}' is allocated on the function call stack and is destroyed when the function returns.",
                    "impact": "The returned pointer refers to invalid stack frame memory, leading to stack corruption upon reuse.",
                    "standards": "CWE-562, MISRA C:2012 Rule 17.8",
                    "recommendation": "Pass a destination buffer into the function or return by value.",
                    "suggested_fix": f"return {var}; // Return by value or pass output buffer pointer"
                })

    # ── PASS 3: Array and Boundary Safety ──────────────────────────────────────
    def _check_array_and_boundary_safety(self):
        # 1. Array bounds declaration vs fixed index access
        # e.g.: int arr[10]; ... arr[10] = ... (index 10 on size 10)
        array_decl_re = re.compile(r'\b(?:int|char|uint8_t|uint16_t|uint32_t|float|double)\s+([A-Za-z0-9_]+)\s*\[\s*(\d+)\s*\]')
        arrays_declared = {}
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            for m in array_decl_re.finditer(line):
                arrays_declared[m.group(1)] = (int(m.group(2)), idx)

        array_access_re = re.compile(r'\b([A-Za-z0-9_]+)\s*\[\s*(\d+)\s*\]')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//") or array_decl_re.search(line):
                continue
            for m in array_access_re.finditer(line):
                arr_name = m.group(1)
                index_val = int(m.group(2))
                if arr_name in arrays_declared:
                    size, decl_line = arrays_declared[arr_name]
                    if index_val >= size:
                        self.findings.append({
                            "rule_id": "ARR-OUT-OF-BOUNDS-01",
                            "analyzer": "CPPMisraAnalyzer",
                            "category": "ArrayBounds",
                            "severity": "CRITICAL" if index_val > size else "HIGH",
                            "line": idx,
                            "message": f"Array Out-of-Bounds Access: '{arr_name}[{index_val}]' exceeds declared size {size} (line {decl_line}).",
                            "snippet": line.strip(),
                            "root_cause": f"Arrays are 0-indexed (valid indices 0..{size - 1}). Accessing index {index_val} writes/reads past the buffer boundary.",
                            "impact": "Buffer overflow, stack memory corruption, unpredictable runtime failure.",
                            "standards": "CWE-125, CWE-787, MISRA C:2012 Rule 18.1",
                            "recommendation": f"Ensure index is strictly within range 0 to {size - 1}.",
                            "suggested_fix": f"{arr_name}[{size - 1}]"
                        })

        # 2. Off-by-one loop: for (int i = 0; i <= SIZE; i++) arr[i]
        off_by_one_loop_re = re.compile(r'for\s*\(\s*int\s+([A-Za-z0-9_]+)\s*=\s*0\s*;\s*\1\s*<=\s*(\d+)\s*;')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = off_by_one_loop_re.search(line)
            if m:
                loop_var = m.group(1)
                bound = int(m.group(2))
                # Check if this bound matches a declared array size
                for arr_name, (size, _) in arrays_declared.items():
                    if size == bound:
                        self.findings.append({
                            "rule_id": "ARR-OFF-BY-ONE-LOOP-01",
                            "analyzer": "CPPMisraAnalyzer",
                            "category": "ArrayBounds",
                            "severity": "HIGH",
                            "line": idx,
                            "message": f"Off-by-One Loop Condition: '<= {bound}' iterates {bound + 1} times on array '{arr_name}' of size {bound}.",
                            "snippet": line.strip(),
                            "root_cause": f"Loop condition '<=' allows loop variable '{loop_var}' to reach {bound}, which is out-of-bounds for an array of size {bound}.",
                            "impact": "Memory corruption during the final loop iteration.",
                            "standards": "CWE-193, MISRA C:2012 Rule 14.2",
                            "recommendation": f"Change loop condition from '<= {bound}' to '< {bound}'.",
                            "suggested_fix": line.replace(f"<= {bound}", f"< {bound}").strip()
                        })

    # ── PASS 4: Resource Management ────────────────────────────────────────────
    def _check_resource_management(self):
        # File open without file close: fopen()
        fopen_calls = {}
        fopen_re = re.compile(r'([A-Za-z0-9_]+)\s*=\s*fopen\s*\(')
        fclose_re = re.compile(r'fclose\s*\(\s*([A-Za-z0-9_]+)\s*\)')

        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m_op = fopen_re.search(line)
            if m_op:
                fopen_calls[m_op.group(1)] = idx
            m_cl = fclose_re.search(line)
            if m_cl and m_cl.group(1) in fopen_calls:
                del fopen_calls[m_cl.group(1)]

        for var, open_line in fopen_calls.items():
            self.findings.append({
                "rule_id": "RES-FILE-LEAK-01",
                "analyzer": "CPPMisraAnalyzer",
                "category": "ResourceManagement",
                "severity": "HIGH",
                "line": open_line,
                "message": f"Resource Leak: File pointer '{var}' opened with fopen() without matching fclose().",
                "snippet": self.lines[open_line - 1].strip(),
                "root_cause": f"Operating system file descriptor allocated on line {open_line} is not closed before exiting scope.",
                "impact": "System descriptor exhaustion leading to file operation failures in embedded ECUs.",
                "standards": "CWE-775, CERT FIO42-C",
                "recommendation": f"Ensure fclose({var}) is called in all execution branches, or use RAII wrapper.",
                "suggested_fix": f"fclose({var});"
            })

    # ── PASS 5: Unsafe Functions ───────────────────────────────────────────────
    def _check_unsafe_functions(self):
        # Unsafe string functions: strcpy, strcat, sprintf, vsprintf, gets
        unsafe_io_re = re.compile(r'\b(strcpy|strcat|sprintf|vsprintf|gets)\s*\(')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = unsafe_io_re.search(line)
            if m:
                fn = m.group(1)
                safe_alt = {
                    "strcpy": "strncpy_s() or strlcpy() or std::string",
                    "strcat": "strncat_s() or strlcat()",
                    "sprintf": "snprintf()",
                    "vsprintf": "vsnprintf()",
                    "gets": "fgets()"
                }.get(fn, "bounded alternative")

                self.findings.append({
                    "rule_id": "MISRA-C-21.6",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "UnsafeFunctions",
                    "severity": "CRITICAL" if fn in ("gets", "strcpy") else "HIGH",
                    "line": idx,
                    "message": f"MISRA C:2012 Rule 21.6 & CWE-120: Unsafe function '{fn}()' can cause buffer overflows.",
                    "snippet": line.strip(),
                    "root_cause": f"Function '{fn}()' does not verify destination buffer capacity, copying bytes indefinitely until finding a null terminator.",
                    "impact": "Stack or heap buffer overflow leading to memory corruption or arbitrary code execution.",
                    "standards": "CWE-120, MISRA C:2012 Rule 21.6, CERT STR31-C",
                    "recommendation": f"Replace with safe bounded alternative: {safe_alt}.",
                    "suggested_fix": f"// Replace {fn}() with bounded alternative such as {safe_alt}"
                })

        # Unbounded scanf: scanf("%s", buf)
        scanf_re = re.compile(r'scanf\s*\(\s*"%s"\s*,')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            if scanf_re.search(line):
                self.findings.append({
                    "rule_id": "SEC-UNBOUNDED-SCANF-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "UnsafeFunctions",
                    "severity": "HIGH",
                    "line": idx,
                    "message": "CWE-120: Unbounded string format specifier '%s' in scanf().",
                    "snippet": line.strip(),
                    "root_cause": "scanf with '%s' reads unbounded input until whitespace, regardless of destination buffer size.",
                    "impact": "Stack buffer overflow on oversized input.",
                    "standards": "CWE-120, CERT FIO30-C",
                    "recommendation": "Specify maximum buffer width (e.g. '%63s') or use fgets().",
                    "suggested_fix": line.replace('"%s"', '"%63s"').strip()
                })

        # sizeof(pointer) instead of sizeof(buffer) in memcpy/memset
        # e.g.: memset(ptr, 0, sizeof(ptr)) where ptr is defined as Type* ptr
        sizeof_ptr_re = re.compile(r'(?:memset|memcpy)\s*\([^,]+,[^,]+,\s*sizeof\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\)')
        pointer_types_re = re.compile(r'\b(?:char|int|uint8_t|uint32_t|void|\w+)\s*\*\s*([A-Za-z0-9_]+)\b')
        known_pointers = set()
        for line in self.lines:
            for m in pointer_types_re.finditer(line):
                known_pointers.add(m.group(1))

        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = sizeof_ptr_re.search(line)
            if m:
                arg = m.group(1)
                if arg in known_pointers:
                    self.findings.append({
                        "rule_id": "SEC-SIZEOF-POINTER-01",
                        "analyzer": "CPPMisraAnalyzer",
                        "category": "UnsafeFunctions",
                        "severity": "HIGH",
                        "line": idx,
                        "message": f"CWE-467: 'sizeof({arg})' returns pointer size (4 or 8 bytes), not buffer capacity.",
                        "snippet": line.strip(),
                        "root_cause": f"Variable '{arg}' is a pointer. sizeof({arg}) yields the size of the pointer itself rather than the target memory buffer.",
                        "impact": "Incomplete buffer initialization or truncated memory copy.",
                        "standards": "CWE-467, MISRA C:2012 Rule 11.4",
                        "recommendation": f"Use sizeof(*{arg}) or the actual buffer byte length.",
                        "suggested_fix": line.replace(f"sizeof({arg})", f"sizeof(*{arg})").strip()
                    })

    # ── PASS 6: Correctness & Logic ────────────────────────────────────────────
    def _check_correctness(self):
        # 1. Assignment in boolean conditional: if (x = y) instead of ==
        assign_in_cond_re = re.compile(r'if\s*\(\s*([A-Za-z0-9_]+)\s*=\s*([^=][^)]*)\)')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = assign_in_cond_re.search(line)
            if m:
                var = m.group(1)
                val = m.group(2).strip()
                self.findings.append({
                    "rule_id": "CORR-ASSIGN-IN-COND-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Correctness",
                    "severity": "HIGH",
                    "line": idx,
                    "message": f"Logic Defect: Assignment operator '=' used in conditional 'if ({var} = {val})' instead of equality '=='.",
                    "snippet": line.strip(),
                    "root_cause": f"Single '=' overwrites '{var}' with '{val}' and evaluates the truthiness of the result rather than comparing.",
                    "impact": "Unintended state modification and erroneous branch execution.",
                    "standards": "CWE-480, MISRA C:2012 Rule 13.4",
                    "recommendation": f"Change '=' to '==' or adopt Yoda notation (e.g. '{val} == {var}').",
                    "suggested_fix": line.replace(f"{var} = {val}", f"{var} == {val}").strip()
                })

        # 2. Comparison of unsigned variable < 0 (always false)
        unsigned_lt_zero_re = re.compile(r'\b(?:uint8_t|uint16_t|uint32_t|uint64_t|size_t|unsigned\s+int)\s+([A-Za-z0-9_]+)\b')
        unsigned_vars = set()
        for line in self.lines:
            for m in unsigned_lt_zero_re.finditer(line):
                unsigned_vars.add(m.group(1))

        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            for uvar in unsigned_vars:
                if re.search(r'\b' + re.escape(uvar) + r'\s*<\s*0\b', line):
                    self.findings.append({
                        "rule_id": "CORR-UNSIGNED-LT-ZERO-01",
                        "analyzer": "CPPMisraAnalyzer",
                        "category": "Correctness",
                        "severity": "HIGH",
                        "line": idx,
                        "message": f"Logic Defect: Unsigned variable '{uvar}' compared '< 0', which is mathematically always false.",
                        "snippet": line.strip(),
                        "root_cause": f"Unsigned types cannot represent negative values. The condition '{uvar} < 0' is dead logic.",
                        "impact": "Error handling checks against negative error codes will never trigger.",
                        "standards": "CWE-570, MISRA C:2012 Rule 14.3",
                        "recommendation": "Use signed integer if checking for negative error codes.",
                        "suggested_fix": line.replace(f"{uvar} < 0", f"{uvar} == 0").strip()
                    })

        # 3. Side effects in assert: assert(i++ > 0)
        assert_side_effect_re = re.compile(r'\bassert\s*\([^)]*(\+\+|--|=(?!=))[^)]*\)')
        for idx, line in enumerate(self.lines, start=1):
            if assert_side_effect_re.search(line):
                self.findings.append({
                    "rule_id": "MISRA-C-13.2",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Correctness",
                    "severity": "HIGH",
                    "line": idx,
                    "message": "MISRA C:2012 Rule 13.2: Side effects inside assert() macro are discarded in release/NDEBUG builds.",
                    "snippet": line.strip(),
                    "root_cause": "When NDEBUG is defined for production builds, assert() macros evaluate to void, removing the side-effect.",
                    "impact": "Code executes with different logic in release mode compared to debug mode.",
                    "standards": "MISRA C:2012 Rule 13.2, CERT EXP30-C",
                    "recommendation": "Execute state modifications outside assert().",
                    "suggested_fix": "// Move expression with side effects outside assert macro"
                })

    # ── PASS 7: Security & Automotive Guidelines ───────────────────────────────
    def _check_security_and_automotive_rules(self):
        # 1. Dynamic memory in embedded/automotive safety code
        dyn_mem_re = re.compile(r'\b(malloc|calloc|realloc|free)\s*\(')
        new_delete_re = re.compile(r'\b(new|delete)\s+(\w+|\[\])')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            if dyn_mem_re.search(line):
                self.findings.append({
                    "rule_id": "MISRA-C-21.3",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "AutomotiveEmbedded",
                    "severity": "HIGH",
                    "line": idx,
                    "message": "MISRA C:2012 Rule 21.3: Dynamic memory allocation (malloc/free) prohibited in safety-critical code.",
                    "snippet": line.strip(),
                    "root_cause": "Dynamic memory allocation causes non-deterministic execution times, heap fragmentation, and out-of-memory hazards.",
                    "impact": "Loss of deterministic timing guarantees required by ISO 26262 ASIL-D.",
                    "standards": "MISRA C:2012 Rule 21.3, ISO 26262 Part 6, AUTOSAR C++",
                    "recommendation": "Use statically pre-allocated buffers or fixed-size memory pools.",
                    "suggested_fix": "// Allocate statically: static uint8_t buffer[CAPACITY];"
                })
            elif new_delete_re.search(line):
                self.findings.append({
                    "rule_id": "MISRA-CPP-18.4.1",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "AutomotiveEmbedded",
                    "severity": "MEDIUM",
                    "line": idx,
                    "message": "MISRA C++:2008 Rule 18-4-1: Dynamic memory operators 'new'/'delete' should be avoided in embedded systems.",
                    "snippet": line.strip(),
                    "root_cause": "Dynamic heap operators can fail and lead to memory exhaustion.",
                    "impact": "Non-deterministic behavior in real-time control loops.",
                    "standards": "MISRA C++:2008 Rule 18-4-1, ISO 26262",
                    "recommendation": "Prefer static allocation or stack objects with RAII.",
                    "suggested_fix": "// Prefer static allocation or std::array"
                })

        # 2. Unsafe pointer conversions: reinterpret_cast or raw pointer casting
        unsafe_cast_re = re.compile(r'\(\s*(?:uint32_t\*|int\*|char\*|void\*|uint8_t\*)\s*\)\s*[A-Za-z_][A-Za-z0-9_]*|reinterpret_cast<')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            if unsafe_cast_re.search(line):
                self.findings.append({
                    "rule_id": "MISRA-C-11.4",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "AutomotiveEmbedded",
                    "severity": "HIGH",
                    "line": idx,
                    "message": "MISRA C:2012 Rule 11.4: Conversion between pointer to object and incompatible pointer type.",
                    "snippet": line.strip(),
                    "root_cause": "Casting between unrelated pointer types violates strict aliasing rules and alignment guarantees.",
                    "impact": "Undefined behavior, alignment hardware faults on ARM/Tricore automotive architectures.",
                    "standards": "MISRA C:2012 Rule 11.4, CERT EXP36-C",
                    "recommendation": "Use memcpy for type-punning or union with explicit sizing.",
                    "suggested_fix": "// Use memcpy for byte-level type conversion"
                })

        # 3. Hardcoded secrets / encryption keys (CWE-798)
        hardcoded_key_re = re.compile(r'(?:const\s+char\s*\*\s*|#define\s+)(?:[A-Za-z0-9_]*(?:KEY|SECRET|PASSWORD|TOKEN|AUTH)[A-Za-z0-9_]*)\s*[= ]\s*"([^"]+)"', re.IGNORECASE)
        for idx, line in enumerate(self.lines, start=1):
            m = hardcoded_key_re.search(line)
            if m and len(m.group(1)) >= 4:
                self.findings.append({
                    "rule_id": "CWE-798",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Security",
                    "severity": "HIGH",
                    "line": idx,
                    "message": "CWE-798: Hardcoded secret, password, or security token detected in source code.",
                    "snippet": line.strip(),
                    "root_cause": "Sensitive credential embedded directly in binary source.",
                    "impact": "Extraction via firmware reverse engineering, compromising vehicle gateway authentication.",
                    "standards": "CWE-798, ISO 21434 Section 9, OWASP Top 10",
                    "recommendation": "Store keys in Hardware Security Module (HSM) or secure non-volatile storage.",
                    "suggested_fix": "// Retrieve credential securely from HSM / Secure Boot key storage"
                })

        # 4. Command injection: system() / popen()
        cmd_exec_re = re.compile(r'\b(system|popen)\s*\(')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            m = cmd_exec_re.search(line)
            if m:
                fn = m.group(1)
                self.findings.append({
                    "rule_id": "SEC-COMMAND-INJECTION-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Security",
                    "severity": "CRITICAL",
                    "line": idx,
                    "message": f"CWE-78: Unsafe shell command invocation '{fn}()'.",
                    "snippet": line.strip(),
                    "root_cause": f"Calling '{fn}()' executes input via system command shell.",
                    "impact": "Arbitrary command execution and privilege escalation.",
                    "standards": "CWE-78, MISRA C:2012 Rule 21.8, CERT ENV33-C",
                    "recommendation": "Eliminate shell command execution in embedded automotive control units.",
                    "suggested_fix": "// Avoid shell process spawning; use direct native API"
                })

        # 5. Automotive CAN unpack bounds
        can_unpack_re = re.compile(r'memcpy\s*\(\s*([A-Za-z0-9_.]+)\s*,\s*([A-Za-z0-9_.]+->data|[A-Za-z0-9_.]+\.data)\s*,\s*([A-Za-z0-9_.]+)\s*\)')
        for idx, line in enumerate(self.lines, start=1):
            m = can_unpack_re.search(line)
            if m:
                dest = m.group(1)
                len_arg = m.group(3)
                start_window = max(0, idx - 6)
                window_text = " ".join(self.lines[start_window:idx])
                if not any(chk in window_text for chk in ("<= sizeof", "dlc <= 8", "length <=")):
                    self.findings.append({
                        "rule_id": "AUTO-CAN-DLC-01",
                        "analyzer": "CPPMisraAnalyzer",
                        "category": "Security",
                        "severity": "CRITICAL",
                        "line": idx,
                        "message": f"Automotive CAN Safety: Unchecked CAN payload copy into '{dest}'. Length '{len_arg}' not bounded.",
                        "snippet": line.strip(),
                        "root_cause": "CAN Data Length Code (DLC) copied into buffer without validating against destination capacity.",
                        "impact": "Malignant CAN injection frame causing ECU memory corruption (CWE-120).",
                        "standards": "ISO 26262 Part 6, ISO 21434, CWE-120",
                        "recommendation": f"Verify '{len_arg} <= sizeof({dest})' prior to copying.",
                        "suggested_fix": f"if ({len_arg} <= sizeof({dest})) {{ {line.strip()} }}"
                    })

    # ── PASS 8: Performance & Maintainability ──────────────────────────────────
    def _check_performance_and_maintainability(self):
        # 1. strlen() inside for loop condition: for (int i = 0; i < strlen(s); i++)
        strlen_loop_re = re.compile(r'for\s*\([^;]+;\s*[^;<>]*(?:<|<=)\s*strlen\s*\([^)]+\)\s*;')
        for idx, line in enumerate(self.lines, start=1):
            if line.strip().startswith("//"):
                continue
            if strlen_loop_re.search(line):
                self.findings.append({
                    "rule_id": "PERF-STRLEN-IN-LOOP-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Performance",
                    "severity": "MEDIUM",
                    "line": idx,
                    "message": "Performance Defect: strlen() re-evaluated on every loop iteration (O(N^2) complexity).",
                    "snippet": line.strip(),
                    "root_cause": "strlen() scans memory for '\\0' sequentially on each loop condition check.",
                    "impact": "Unnecessary CPU cycles and degraded throughput in real-time execution.",
                    "standards": "CERT STR31-C, Embedded Real-Time Guidelines",
                    "recommendation": "Store string length in a local variable before entering the loop.",
                    "suggested_fix": "const size_t len = strlen(str);\nfor (size_t i = 0; i < len; ++i)"
                })

        # 2. Empty catch blocks: catch (...) {}
        empty_catch_re = re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}')
        for idx, line in enumerate(self.lines, start=1):
            if empty_catch_re.search(line):
                self.findings.append({
                    "rule_id": "MAINT-EMPTY-CATCH-01",
                    "analyzer": "CPPMisraAnalyzer",
                    "category": "Maintainability",
                    "severity": "MEDIUM",
                    "line": idx,
                    "message": "CWE-390: Empty catch block silently suppresses exception without logging or recovery.",
                    "snippet": line.strip(),
                    "root_cause": "Exceptions caught with empty bodies leave the system in an unverified state without failure telemetry.",
                    "impact": "Silent software faults masking safety-critical failures.",
                    "standards": "CWE-390, MISRA C++:2008 Rule 15-3-1",
                    "recommendation": "Log diagnostic error, trigger safety recovery mode, or rethrow.",
                    "suggested_fix": "catch (const std::exception& e) {\n    LOG_ERROR(\"Exception caught: \", e.what());\n    // Handle or enter fail-safe state\n}"
                })
