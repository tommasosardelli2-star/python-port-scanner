import asyncio
import socket
import time
from collections import Counter

# ---------------------------------------------------------------------------
# Configuration (identical in port_scanner_threads.py)
# ---------------------------------------------------------------------------
HOST = "127.0.0.1"
START_PORT = 1
END_PORT = 1000
CONCURRENCY = 1000  # size of the semaphore (max simultaneous connections)
TIMEOUT = 4.0       # seconds to wait for each connection

# Output filter. Open ports and errors are always shown.
# 0 = nothing else
# 1 = also filtered ports
# 2 = all ports
# 3 = also closed ports
FILTER_MODE = 0


async def scanner(host, port, semaphore):
    """Try a TCP connection to one port and return (port, state, detail)."""
    # Acquire a slot in the shared semaphore; "async with" releases it automatically
    async with semaphore:
        # Only the connection attempt is inside this try: it decides the port state
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=TIMEOUT
            )
        except asyncio.TimeoutError:
            return (port, "filtered", "timeout")
        except ConnectionRefusedError as e:
            return (port, "close", str(e))
        # Generic error, e.g. network unreachable or access denied by the OS
        except OSError as e:
            return (port, "error", str(e))

        # The connection succeeded: the port is open
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass  # Even if closing the writer fails, the port is still open

        # The service name is only extra information and must never change the state
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


async def main():
    start = time.perf_counter()
    # One semaphore shared by all tasks limits the simultaneous connections
    semaphore = asyncio.Semaphore(CONCURRENCY)
    # Calling an async function does not run it: it returns a coroutine object
    # that gather will schedule
    tasks = [scanner(HOST, port, semaphore) for port in range(START_PORT, END_PORT + 1)]
    # gather takes the coroutines as separate arguments, so the list is unpacked with *
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    print_report(results, elapsed)


if __name__ == "__main__":
    asyncio.run(main())