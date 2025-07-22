#!/usr/bin/env python3
"""
Sourcerer Application Runner
Provides multiple ways to run the Sourcerer application
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_backend(host="127.0.0.1", port=8000, reload=False, debug=False):
    """Run the backend FastAPI server"""
    print(f"Starting Sourcerer backend server on {host}:{port}")
    
    cmd = [
        sys.executable, "-m", "backend.main",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    if debug:
        cmd.append("--debug")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nBackend server stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error running backend: {e}")
        return False
    
    return True


def run_frontend():
    """Run the frontend development server"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    if not frontend_dir.exists():
        print("Frontend directory not found")
        return False
    
    print("Starting frontend development server...")
    
    # Check if dependencies are installed
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies...")
        result = subprocess.run(
            ["npm", "install"],
            cwd=frontend_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("Failed to install dependencies:")
            print(result.stderr)
            return False
    
    # Start development server
    try:
        subprocess.run(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            check=True
        )
    except KeyboardInterrupt:
        print("\nFrontend server stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error running frontend: {e}")
        return False
    
    return True


def build_frontend():
    """Build the frontend for production"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    if not frontend_dir.exists():
        print("Frontend directory not found")
        return False
    
    print("Building frontend for production...")
    
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True
        )
        print("Frontend built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building frontend: {e}")
        return False


def run_tests():
    """Run the test suite"""
    print("Running Sourcerer tests...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v",
            "--tb=short"
        ], check=True)
        print("All tests passed!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Tests failed: {e}")
        return False


def run_doctor():
    """Run diagnostics"""
    print("Running Sourcerer diagnostics...")
    
    try:
        subprocess.run([
            sys.executable, "-m", "backend.main",
            "--doctor"
        ], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Diagnostics failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Sourcerer Application Runner")
    parser.add_argument(
        "command",
        choices=["backend", "frontend", "build", "test", "doctor", "full"],
        help="Command to run"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind backend to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind backend to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for backend")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.command == "backend":
        return run_backend(args.host, args.port, args.reload, args.debug)
    
    elif args.command == "frontend":
        return run_frontend()
    
    elif args.command == "build":
        return build_frontend()
    
    elif args.command == "test":
        return run_tests()
    
    elif args.command == "doctor":
        return run_doctor()
    
    elif args.command == "full":
        # Build frontend first
        if not build_frontend():
            return False
        
        # Then run backend with built frontend
        return run_backend(args.host, args.port, args.reload, args.debug)
    
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)