import socket
import sys

def check_port(host, port, service_name):
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f"✅ {service_name} is running on {host}:{port}")
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        print(f"❌ {service_name} is NOT running on {host}:{port}")
        return False

def main():
    print("Checking services...")
    redis_ok = check_port("localhost", 6380, "Redis")
    mongo_ok = check_port("localhost", 27017, "MongoDB")
    
    if not redis_ok or not mongo_ok:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
