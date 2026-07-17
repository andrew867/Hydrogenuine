#!/usr/bin/env python3
"""
Run all automation script tests and generate a summary report.
"""

import sys
import subprocess
from pathlib import Path

workspace_root = Path(__file__).parent.parent


def run_tests():
    """Run all test suites and report results"""
    print("=" * 70)
    print("AUTOMATION SCRIPTS TEST SUITE")
    print("=" * 70)
    print()
    
    test_files = [
        "tests/test_moltbook_scripts.py",
        "tests/test_fourclaw_scripts.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        test_path = workspace_root / test_file
        if not test_path.exists():
            print(f"⚠️  Test file not found: {test_file}")
            continue
        
        print(f"Running: {test_file}")
        print("-" * 70)
        
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        results[test_file] = {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "output": result.stdout
        }
        
        print()
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total_passed = sum(1 for r in results.values() if r["passed"])
    total_tests = len(results)
    
    for test_file, result in results.items():
        status = "[PASSED]" if result["passed"] else "[FAILED]"
        print(f"{status}: {test_file}")
    
    print()
    print(f"Total test suites: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    
    if total_passed == total_tests:
        print()
        print("SUCCESS: All test suites passed!")
        return 0
    else:
        print()
        print("WARNING: Some test suites failed. Check output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
