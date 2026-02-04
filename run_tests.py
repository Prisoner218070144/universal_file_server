"""
Enhanced test runner with coverage reporting and test selection options
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_tests_with_coverage(test_paths=None, html_report=False, verbose=False):
    """Run tests with coverage reporting"""

    # Base command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=app",
        "--cov=controllers",
        "--cov=models",
        "--cov=utils",
        "--cov-report=term",
        "--cov-report=xml:coverage.xml",
    ]

    # Add HTML report if requested
    if html_report:
        cmd.append("--cov-report=html:coverage_html")

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add test paths
    if test_paths:
        cmd.extend(test_paths)
    else:
        cmd.append("tests/")

    # Run the command
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    return result.returncode


def run_specific_test_type(test_type, html_report=False, verbose=False):
    """Run specific type of tests"""

    test_paths = {
        "unit": "tests/unit/",
        "integration": "tests/integration/",
        "functional": "tests/functional/",
        "helpers": "tests/unit/test_helpers.py",
        "upload": "tests/unit/test_upload_handler.py",
        "routes": "tests/unit/test_routes*.py",
        "all": "tests/",
    }

    if test_type not in test_paths:
        print(f"Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_paths.keys())}")
        return 1

    return run_tests_with_coverage(
        test_paths=[test_paths[test_type]], html_report=html_report, verbose=verbose
    )


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run tests with coverage reporting")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        help="Type of tests to run (unit, integration, functional, helpers, upload, routes, all)",
    )
    parser.add_argument(
        "--html", action="store_true", help="Generate HTML coverage report"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--paths", nargs="+", help="Specific test paths to run")
    parser.add_argument(
        "--run-slow", action="store_true", help="Run tests marked as slow"
    )

    args = parser.parse_args()

    # Set environment variable for slow tests
    if args.run_slow:
        os.environ["RUN_SLOW_TESTS"] = "1"

    if args.paths:
        # Run tests on specific paths
        return run_tests_with_coverage(
            test_paths=args.paths, html_report=args.html, verbose=args.verbose
        )
    else:
        # Run specific test type
        return run_specific_test_type(
            test_type=args.test_type, html_report=args.html, verbose=args.verbose
        )


if __name__ == "__main__":
    sys.exit(main())
