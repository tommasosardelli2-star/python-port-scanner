import socket
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat

# ---------------------------------------------------------------------------
# Configuration (identical in port_scanner_async.py)
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
START_PORT = 1
END_PORT = 1000
CONCURRENCY = 1000  # number of worker threads
TIMEOUT = 4.0       # seconds to wait for each connection

# Output filter. Open ports and errors are always shown.
# 0 = nothing else
# 1 = also filtered ports
# 2 = all ports
# 3 = also closed ports
FILTER_MODE = 0


def scanner(host, port):
    """Try a TCP connection to one port and return (port, state, detail)."""
    # The try covers socket creation too, so no exception can escape from here
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(TIMEOUT)
            s.connect((host, port))
    except ConnectionRefusedError as e:
        return (port, "close", str(e))
    except TimeoutError:
        return (port, "filtered", "timeout")
    # Generic error, e.g. network unreachable or access denied by the OS
    except OSError as e:
        return (port, "error", str(e))

    # The connection succeeded: the port is open. The service name is only
    # extra information and must never change the state.
    try:
        info = socket.getservbyport(port, "tcp")
    except OSError:
        info = "No standard service found"
    return (port, "open", info)


def print_report(results, elapsed):
    counts = Counter()
    for port, state, detail in results:
        counts[state] += 1
        if state == "open":
            print(f"Port: {port} State: {state} Info: {detail}")
        elif state == "error":
            print(f"Port: {port} State: {state} Detail: {detail}")
        elif (FILTER_MODE == 2
              or (FILTER_MODE == 1 and state == "filtered")
              or (FILTER_MODE == 3 and state == "close")):
            print(f"Port: {port} State: {state}")
    print(f"Open: {counts['open']}, Filtered: {counts['filtered']}, "
          f"Closed: {counts['close']}, Error: {counts['error']}")
    print(f"Time = {elapsed:.3f}")


def main():
    start = time.perf_counter()
    ports = range(START_PORT, END_PORT + 1)
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        # repeat(HOST) gives the same host for every port; map stops at the
        # shortest iterable, so it ends with the ports. list() waits for all results.
        results = list(ex.map(scanner, repeat(HOST), ports))
    elapsed = time.perf_counter() - start
    print_report(results, elapsed)


if __name__ == "__main__":
    main()
