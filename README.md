# Python Port Scanner

A concurrent TCP connect port scanner written in Python, implemented twice to compare two concurrency models: **threads** (`ThreadPoolExecutor`) and **asyncio**.

Built as a learning project to practice networking fundamentals (TCP handshake, port states) and concurrency in Python.

> **Legal notice:** use this tool only on systems you own or have explicit permission to test (your own machines, a local lab, or authorized training platforms). Scanning other people's systems without authorization may be illegal.

## Features

- TCP connect scan on a configurable range of ports (default: 1-1000)
- Two implementations with the same logic:
  - `PortScannerMultiThreads.py`: thread pool with `concurrent.futures`
  - `PortScannerAsync.py`: `asyncio` with a semaphore limiting concurrency
- Results returned in port order
- Each port is classified as `open`, `close`, `filtered` or `error`
- Conventional service name for open ports (via `socket.getservbyport`)
- Final summary with the count of each state and the total scan time
- Same configuration, output format and summary in both versions
- Configurable output filter (open ports and errors are always shown)
- Errors are handled inside each scan task, so one failure never stops the whole scan

## Requirements

- Python 3.10 or newer
- No external libraries: only the standard library is used

## Usage

1. Open the script you want to run and edit the configuration constants at the top of the file (they are identical in both versions):

   ```python
   HOST = "127.0.0.1"
   START_PORT = 1
   END_PORT = 1000
   CONCURRENCY = 1000   # worker threads / semaphore size
   TIMEOUT = 4.0        # seconds per connection
   FILTER_MODE = 0      # 0 = only open ports, 1 = + filtered, 2 = all, 3 = + closed
   ```

   Open ports and errors are always shown, whatever the filter is.

2. Run it:

   ```bash
   python port_scanner_async.py
   ```

To try it safely, start a test server in another terminal and scan your own machine:

```bash
python -m http.server 8000
```

### Example output (illustrative)

```
Port: 8000 State: open Info: No standard service found
Open: 1, Filtered: 0, Closed: 999, Error: 0
Time = 2.302
```

## How it works

The scanner performs a full **TCP connect** scan: for each port it tries to complete the three-way handshake and interprets the outcome.

| State | What happened | Meaning |
|---|---|---|
| `open` | The connection was established | A service is listening |
| `close` | The connection was refused (RST) | Nothing is listening, host reachable |
| `filtered` | No answer within the timeout | Packets dropped, or the timeout is too short |
| `error` | Another OS or network error | Reported with the error message |

Each scan task always returns a tuple `(port, state, detail)`, so printing and counting are kept separate from the scanning logic.

### Threads vs asyncio

Both versions do the same work: a network connection spends almost all of its time **waiting**, so the job is I/O-bound.

- **Threads:** a pool of worker threads, each one waiting on its own connection.
- **asyncio:** a single thread with an event loop; tasks yield control while waiting. A semaphore limits how many connections are in flight, and `asyncio.wait_for` provides the timeout.

#### Measured times

Single measurements against a lab target reached through a VPN (repeat the tests and average them for reliable numbers):

| Concurrency | Threads | asyncio |
|---|---|---|
| 100 | 29.4 s | 29.8 s |
| 1000 | 3.8 s | 4.7 s |

**Conclusion:** with this kind of workload the total time is dominated by the connection timeout, not by the concurrency model, so the two versions perform about the same. The advantage of asyncio is not speed at low concurrency but **resource usage**: coroutines are much lighter than threads, which matters when the number of simultaneous connections grows.

## Verification

Results were compared with `nmap -p 1-1000` against the same lab target: the open ports matched.

## Limitations

- **"filtered" is an inference.** It means "no answer within the timeout", not necessarily "a firewall dropped the packets". A timeout that is too short can misclassify ports.
- **Windows behaviour.** With a short timeout (2 s) closed ports were reported as `filtered`, because the OS takes about two seconds to report a refused connection. A timeout of 4 s fixed it.
- **Service names are conventional.** `getservbyport` returns the name usually associated with a port, not what is actually listening there (SSH on port 8080 would still be reported as "http-alt").
- **Connect scan is noisy.** Completing the handshake leaves traces in the target's logs, unlike a SYN scan (which needs raw sockets and elevated privileges).
- **TCP only.** UDP scanning is not supported.
- **Results arrive at the end.** With `asyncio.gather` nothing is printed until the whole scan is complete.
- Very high concurrency can exhaust the operating system's open-file limits and produce `error` results.
- On Windows, scanning `127.0.0.1` may report some ports (e.g. 137) as `error` with `WinError 10013` (access denied by the OS). The state of those ports cannot be determined, so they are reported as errors instead of guessed.

## Possible improvements

- Command-line arguments with `argparse` (host, port range, concurrency, timeout)
- Banner grabbing to identify the real service and version
- Export of results to JSON or CSV
- Live progress output

## What I learned

- How the TCP handshake maps to open, closed and filtered ports
- Thread pools and race-free result handling in Python
- `asyncio`: coroutines, `await`, `gather`, semaphores and timeouts
- Why a timeout, not the concurrency model, can be the bottleneck
- Exception handling in concurrent code, so that one failure never loses all the other results