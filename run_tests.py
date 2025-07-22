#!/usr/bin/env python3
"""
Test runner for Sourcerer end-to-end tests.
Handles test server startup, test execution, and cleanup.
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path
from typing import Optional

def start_test_server() -> Optional[subprocess.Popen]:
    """Start the Sourcerer server for testing"""
    
    print("Starting test server...")
    
    # Set test environment variables
    env = os.environ.copy()
    env.update({
        "SOURCERER_ENV": "test",
        "SOURCERER_HOST": "127.0.0.1",
        "SOURCERER_PORT": "8000",
        "SOURCERER_LOG_LEVEL": "INFO"
    })
    
    try:
        # Start server using uvicorn
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "info"
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(5)
        
        # Check if server is running
        import httpx
        try:
            response = httpx.get("http://127.0.0.1:8000/api/config/validation", timeout=10.0)
            if response.status_code == 200:
                print("✓ Test server is running")
                return process
            else:
                print(f"✗ Server responded with status {response.status_code}")
                process.terminate()
                return None
        except Exception as e:
            print(f"✗ Failed to connect to server: {e}")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return None

def stop_test_server(process: subprocess.Popen):
    """Stop the test server"""
    
    print("Stopping test server...")
    
    try:
        # Send SIGTERM
        process.terminate()
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=10)
            print("✓ Server stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if needed
            process.kill()
            process.wait()
            print("✓ Server force stopped")
            
    except Exception as e:
        print(f"Warning: Error stopping server: {e}")

def run_tests(test_type: str = "all", verbose: bool = False, specific_test: Optional[str] = None) -> int:
    """Run the specified tests"""
    
    print(f"Running {test_type} tests...")
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    # Add test selection based on type
    if test_type == "e2e":
        cmd.extend(["-m", "e2e", "tests/e2e/"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration", "tests/integration/"])
    elif test_type == "unit":
        cmd.extend(["-m", "unit", "tests/unit/"])
    elif test_type == "all":
        cmd.append("tests/")
    
    # Add specific test if provided
    if specific_test:
        cmd.append(specific_test)
    
    # Add other pytest options
    cmd.extend([
        "--tb=short",  # Shorter traceback format
        "--durations=10",  # Show 10 slowest tests
        "-x"  # Stop on first failure
    ])
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"✗ Error running tests: {e}")
        return 1

def setup_test_environment():
    """Set up the test environment"""
    
    print("Setting up test environment...")
    
    # Create test directories
    project_root = Path(__file__).parent
    test_data_dir = project_root / "test_data"
    test_logs_dir = project_root / "test_logs"
    
    test_data_dir.mkdir(exist_ok=True)
    test_logs_dir.mkdir(exist_ok=True)
    
    print("✓ Test directories created")

def cleanup_test_environment():
    """Clean up test environment"""
    
    print("Cleaning up test environment...")
    
    try:
        import shutil
        project_root = Path(__file__).parent
        
        # Clean up test data
        test_data_dir = project_root / "test_data"
        test_logs_dir = project_root / "test_logs"
        
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
        if test_logs_dir.exists():
            shutil.rmtree(test_logs_dir)
        
        print("✓ Test environment cleaned")
    except Exception as e:
        print(f"Warning: Cleanup error: {e}")

def main():
    """Main test runner function"""
    
    parser = argparse.ArgumentParser(description="Run Sourcerer tests")
    parser.add_argument(
        "test_type", 
        choices=["all", "e2e", "integration", "unit"],
        default="all",
        nargs="?",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-t", "--test",
        help="Specific test file or test case to run"
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start test server (assume it's already running)"
    )
    parser.add_argument(
        "--keep-server",
        action="store_true", 
        help="Keep server running after tests"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test environment and exit"
    )
    
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_environment()
        return 0
    
    # Set up test environment
    setup_test_environment()
    
    server_process = None
    exit_code = 0
    
    try:
        # Start server if needed
        if not args.no_server and args.test_type in ["all", "e2e", "integration"]:
            server_process = start_test_server()
            if not server_process:
                print("✗ Failed to start test server")
                return 1
        
        # Run tests
        exit_code = run_tests(args.test_type, args.verbose, args.test)
        
        if exit_code == 0:
            print("✓ All tests passed!")
        else:
            print(f"✗ Tests failed with exit code {exit_code}")
    
    except KeyboardInterrupt:
        print("\n⚠ Tests interrupted by user")
        exit_code = 130
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        exit_code = 1
    
    finally:
        # Stop server if we started it
        if server_process and not args.keep_server:
            stop_test_server(server_process)
        
        # Cleanup unless keeping server
        if not args.keep_server:
            cleanup_test_environment()
    
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)