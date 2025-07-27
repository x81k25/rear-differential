#!/usr/bin/env python3
# test/run_tests.py
"""Test runner script for integration tests."""
import sys
import os
import subprocess

def main():
    """Run the integration tests."""
    # Add the parent directory to Python path so we can import the app
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    # Install test requirements
    print("Installing test dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "test/requirements.txt"], 
                   cwd=parent_dir, check=True)
    
    # Run pytest
    print("Running integration tests...")
    cmd = [sys.executable, "-m", "pytest", "test/", "-v", "--tb=short"]
    
    # Add any command line arguments passed to this script
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])
    
    result = subprocess.run(cmd, cwd=parent_dir)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()