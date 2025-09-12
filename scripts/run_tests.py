#!/usr/bin/env python3
"""Test runner script for the Kachi billing system."""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        if result.stdout:
            print(result.stdout)
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr:
            print("STDERR:", result.stderr)
        if result.stdout:
            print("STDOUT:", result.stdout)
        return False

    return True


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run tests for Kachi billing system")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument(
        "--performance", action="store_true", help="Run performance tests only"
    )
    parser.add_argument(
        "--property", action="store_true", help="Run property-based tests only"
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--parallel", "-n", type=int, help="Number of parallel workers")

    args = parser.parse_args()

    # Change to project root
    project_root = Path(__file__).parent.parent
    subprocess.run(["cd", str(project_root)], shell=True, check=False)

    success = True

    # Base pytest command
    pytest_cmd = ["uv", "run", "pytest"]

    if args.verbose:
        pytest_cmd.append("-v")

    if args.parallel:
        pytest_cmd.extend(["-n", str(args.parallel)])

    if args.fast:
        pytest_cmd.extend(["-m", "not slow"])

    # Run specific test categories
    if args.unit:
        cmd = [
            *pytest_cmd,
            "tests/test_deriver.py",
            "tests/test_rater.py",
            "tests/test_lago_integration.py",
        ]
        success &= run_command(cmd, "Unit Tests")

    elif args.integration:
        cmd = [*pytest_cmd, "tests/test_integration.py", "-m", "integration"]
        success &= run_command(cmd, "Integration Tests")

    elif args.performance:
        cmd = [*pytest_cmd, "tests/test_performance.py", "-m", "performance"]
        success &= run_command(cmd, "Performance Tests")

    elif args.property:
        cmd = [*pytest_cmd, "tests/test_property_based.py"]
        success &= run_command(cmd, "Property-Based Tests")

    else:
        # Run all tests in sequence
        test_suites = [
            (["tests/test_deriver.py", "tests/test_rater.py"], "Core Unit Tests"),
            (["tests/test_ingest_api.py"], "API Tests"),
            (["tests/test_dashboard_api.py"], "Dashboard API Tests"),
            (["tests/test_lago_integration.py"], "Lago Integration Tests"),
            (["tests/test_property_based.py"], "Property-Based Tests"),
        ]

        if not args.fast:
            test_suites.extend(
                [
                    (["tests/test_integration.py"], "Integration Tests"),
                    (["tests/test_performance.py"], "Performance Tests"),
                ]
            )

        for test_files, description in test_suites:
            cmd = pytest_cmd + test_files
            success &= run_command(cmd, description)

    # Generate coverage report if requested
    if args.coverage:
        coverage_cmd = [
            "uv",
            "run",
            "pytest",
            "--cov=kachi",
            "--cov-report=html",
            "--cov-report=term-missing",
        ]
        success &= run_command(coverage_cmd, "Coverage Report Generation")

        print("\n📊 Coverage report generated in htmlcov/index.html")

    # Run code quality checks
    print("\n🔍 Running Code Quality Checks")

    quality_checks = [
        (["uv", "run", "ruff", "check", "src/", "tests/"], "Ruff Linting"),
        (
            ["uv", "run", "ruff", "format", "--check", "src/", "tests/"],
            "Ruff Formatting",
        ),
        (["uv", "run", "mypy", "src/kachi"], "MyPy Type Checking"),
    ]

    for cmd, description in quality_checks:
        success &= run_command(cmd, description)

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests and checks PASSED!")
        sys.exit(0)
    else:
        print("💥 Some tests or checks FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
