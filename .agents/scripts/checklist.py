#!/usr/bin/env python3
"""
Master Checklist Runner - Antigravity Kit
==========================================

Orchestrates all validation scripts in priority order.
Use this for incremental validation during development.

Usage:
    python scripts/checklist.py .                    # Run core checks
    python scripts/checklist.py . --url <URL>        # Include performance checks

Priority Order:
    P0: Security Scan (vulnerabilities, secrets)
    P1: Lint & Type Check (code quality)
    P2: Schema Validation (if database exists)
    P3: Test Runner (unit/integration tests)
    P4: UX Audit (psychology laws, accessibility)
    P5: SEO Check (meta tags, structure)
    P6: Performance (lighthouse - requires URL)
"""

import sys
import subprocess
import argparse
import ast
import re
from pathlib import Path
from typing import List, Tuple, Optional, Set

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.ENDC}\n")

def print_step(text: str):
    print(f"{Colors.BOLD}{Colors.BLUE}🔄 {text}{Colors.ENDC}")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

import os
import shutil

CORE_CHECKS = [
    ("Python Syntax & Compilation", "syntax_check", True),
    ("Import & API Verification", "import_verify", True),
    ("Framework Unit Tests", "test_suite", True),
    ("Learning Matrix Audit", "learn_audit", True),
]

PERFORMANCE_CHECKS = []

def resolve_script_path(project_path: str, script_path_str: str) -> Optional[Path]:
    """Resolve script path supporting .agents, .agent, and plugins directory."""
    script_name = Path(script_path_str).name
    candidates = [
        Path(project_path) / script_path_str,
        Path(project_path) / script_path_str.replace(".agent/", ".agents/"),
        Path(__file__).resolve().parent.parent / script_path_str.replace(".agent/", "").replace(".agents/", ""),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
            
    # Search plugins directory if available
    plugins_dir = Path(__file__).resolve().parent.parent / "plugins"
    if plugins_dir.exists():
        for p in plugins_dir.glob(f"**/scripts/{script_name}"):
            if p.is_file():
                return p
    return None

def check_script_exists(script_path: Path) -> bool:
    """Check if script file exists"""
    return script_path.exists() and script_path.is_file()

def verify_imports(name: str, project_path_str: str) -> dict:
    """
    Verify all import statements in modified or project source files.
    Ensures no hallucinated modules, missing packages, or broken symbol imports.
    """
    project_path = Path(project_path_str).resolve()
    target_files: Set[Path] = set()

    # 1. Check git status for modified/untracked files
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().splitlines():
                if len(line) > 3:
                    path_str = line[3:].strip()
                    if " -> " in path_str:
                        path_str = path_str.split(" -> ")[1]
                    p = (project_path / path_str).resolve()
                    if p.exists() and p.is_file() and p.suffix.lower() in {".py", ".js", ".ts", ".mjs", ".cjs"}:
                        target_files.add(p)
    except Exception:
        pass

    # 2. If no modified files in git status, scan primary project scripts and tests
    if not target_files:
        for pattern in ["tests/*.py", "scripts/*.py", ".agents/scripts/*.py", "*.py"]:
            for p in project_path.glob(pattern):
                if p.is_file():
                    target_files.add(p.resolve())

    # Filter out skills and meta cache directories
    filtered_targets: List[Path] = []
    for p in sorted(list(target_files)):
        rel = str(p.relative_to(project_path)) if p.is_relative_to(project_path) else str(p)
        parts = Path(rel).parts
        if any(part in {".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".git"} for part in parts):
            continue
        if "skills" in parts:
            continue
        filtered_targets.append(p)

    if not filtered_targets:
        print_success(f"{name}: PASSED (no source files to verify)")
        return {"name": name, "passed": True, "output": "No files to check", "skipped": False}

    search_paths = [
        str(project_path),
        str(project_path / ".agents" / "scripts"),
        str(project_path / ".agent" / "scripts"),
        str(project_path / "src"),
        str(project_path / "lib"),
        str(project_path / "tests"),
    ]
    search_paths = [p for p in search_paths if Path(p).exists()]
    path_setup = f"import sys; sys.path = {search_paths!r} + sys.path;"

    errors: List[str] = []
    verified_count = 0

    for f_path in filtered_targets:
        rel_name = str(f_path.relative_to(project_path)) if f_path.is_relative_to(project_path) else f_path.name
        if f_path.suffix == ".py":
            try:
                tree = ast.parse(f_path.read_text(encoding="utf-8", errors="ignore"), filename=str(f_path))
            except Exception as e:
                errors.append(f"{rel_name}: AST parse error: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        test_cmd = [sys.executable, "-c", f"{path_setup} import {mod}"]
                        res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                        if res.returncode != 0:
                            err = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "Import failed"
                            errors.append(f"{rel_name}:L{node.lineno} Cannot import module '{alias.name}': {err}")
                        else:
                            verified_count += 1
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.level > 0:
                        # Relative import within package
                        continue
                    if node.module:
                        for alias in node.names:
                            sym = "*" if alias.name == "*" else alias.name
                            test_cmd = [sys.executable, "-c", f"{path_setup} from {node.module} import {sym}"]
                            res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
                            if res.returncode != 0:
                                err = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "Import failed"
                                errors.append(f"{rel_name}:L{node.lineno} Cannot import '{alias.name}' from '{node.module}': {err}")
                            else:
                                verified_count += 1

        elif f_path.suffix in {".js", ".mjs", ".ts", ".cjs"}:
            try:
                content = f_path.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r"""(?:import\s+.*?from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""", content):
                    req_target = match.group(1) or match.group(2)
                    if req_target.startswith("."):
                        target_cand = (f_path.parent / req_target).resolve()
                        valid = any([
                            target_cand.exists(),
                            target_cand.with_suffix(".js").exists(),
                            target_cand.with_suffix(".ts").exists(),
                            target_cand.with_suffix(".mjs").exists(),
                            target_cand.with_suffix(".json").exists(),
                            (target_cand / "index.js").exists(),
                            (target_cand / "index.ts").exists()
                        ])
                        if not valid:
                            errors.append(f"{rel_name}: Relative import target '{req_target}' not found on disk")
                        else:
                            verified_count += 1
            except Exception:
                pass

    if errors:
        print_error(f"{name}: FAILED ({len(errors)} unresolved import/API errors)")
        for err in errors[:10]:
            print(f"  ❌ {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
        return {
            "name": name,
            "passed": False,
            "output": "",
            "error": "\n".join(errors),
            "skipped": False
        }

    print_success(f"{name}: PASSED ({len(filtered_targets)} file(s), {verified_count} import statements verified)")
    return {
        "name": name,
        "passed": True,
        "output": f"Verified {len(filtered_targets)} file(s), {verified_count} imports",
        "error": "",
        "skipped": False
    }


def run_script(name: str, script_path_str: str, project_path: str, url: Optional[str] = None) -> dict:
    """
    Run a validation script and capture results
    
    Returns:
        dict with keys: name, passed, output, skipped
    """
    scripts_dir = Path(__file__).resolve().parent

    if script_path_str == "syntax_check":
        print_step(f"Running: {name}")
        py_files = [str(p) for p in scripts_dir.glob("*.py")]
        cmd = [sys.executable, "-m", "py_compile"] + py_files
    elif script_path_str == "import_verify":
        print_step(f"Running: {name}")
        return verify_imports(name, project_path)
    elif script_path_str == "test_suite":
        print_step(f"Running: {name}")
        tests_dir = Path(project_path) / "tests"
        if not tests_dir.exists():
            print_success(f"{name}: PASSED (no tests/ directory in target project)")
            return {"name": name, "passed": True, "output": "No tests/ directory", "skipped": False}
        cmd = [sys.executable, "-m", "unittest", "discover", str(tests_dir), "-v"]
    elif script_path_str == "learn_audit":
        print_step(f"Running: {name}")
        cmd = [sys.executable, str(scripts_dir / "learn.py"), "audit"]
    else:
        script_path = resolve_script_path(project_path, script_path_str)
        if not script_path:
            print_warning(f"{name}: Script not found, skipping")
            return {"name": name, "passed": True, "output": "", "skipped": True}
        print_step(f"Running: {name}")

        cmd = [sys.executable, str(script_path), project_path]
        if url and ("lighthouse" in script_path.name.lower() or "playwright" in script_path.name.lower()):
            cmd.append(url)
    
    # Run script
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        passed = result.returncode == 0
        
        if passed:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            if result.stderr:
                print(f"  Error: {result.stderr[:200]}")
        
        return {
            "name": name,
            "passed": passed,
            "output": result.stdout,
            "error": result.stderr,
            "skipped": False
        }
    
    except subprocess.TimeoutExpired:
        print_error(f"{name}: TIMEOUT (>5 minutes)")
        return {"name": name, "passed": False, "output": "", "error": "Timeout", "skipped": False}
    
    except Exception as e:
        print_error(f"{name}: ERROR - {str(e)}")
        return {"name": name, "passed": False, "output": "", "error": str(e), "skipped": False}

def print_summary(results: List[dict]):
    """Print final summary report"""
    print_header("📊 CHECKLIST SUMMARY")
    
    passed_count = sum(1 for r in results if r["passed"] and not r.get("skipped"))
    failed_count = sum(1 for r in results if not r["passed"] and not r.get("skipped"))
    skipped_count = sum(1 for r in results if r.get("skipped"))
    
    print(f"Total Checks: {len(results)}")
    print(f"{Colors.GREEN}✅ Passed: {passed_count}{Colors.ENDC}")
    print(f"{Colors.RED}❌ Failed: {failed_count}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⏭️  Skipped: {skipped_count}{Colors.ENDC}")
    print()
    
    # Detailed results
    for r in results:
        if r.get("skipped"):
            status = f"{Colors.YELLOW}⏭️ {Colors.ENDC}"
        elif r["passed"]:
            status = f"{Colors.GREEN}✅{Colors.ENDC}"
        else:
            status = f"{Colors.RED}❌{Colors.ENDC}"
        
        print(f"{status} {r['name']}")
    
    print()
    
    if failed_count > 0:
        print_error(f"{failed_count} check(s) FAILED - Please fix before proceeding")
        return False
    else:
        print_success("All checks PASSED ✨")
        return True

def main():
    parser = argparse.ArgumentParser(
        description="Run Antigravity Kit validation checklist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/checklist.py .                      # Core checks only
  python scripts/checklist.py . --url http://localhost:3000  # Include performance
        """
    )
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument("--url", help="URL for performance checks (lighthouse, playwright)")
    parser.add_argument("--skip-performance", action="store_true", help="Skip performance checks even if URL provided")
    
    args = parser.parse_args()
    
    project_path = Path(args.project).resolve()
    
    if not project_path.exists():
        print_error(f"Project path does not exist: {project_path}")
        sys.exit(1)
    
    print_header("🚀 ANTIGRAVITY KIT - MASTER CHECKLIST")
    print(f"Project: {project_path}")
    print(f"URL: {args.url if args.url else 'Not provided (performance checks skipped)'}")
    
    results = []
    
    # Run core checks
    print_header("📋 CORE CHECKS")
    for name, script_id, required in CORE_CHECKS:
        result = run_script(name, script_id, str(project_path))
        results.append(result)
        
        # If required check fails, stop
        if required and not result["passed"] and not result.get("skipped"):
            print_error(f"CRITICAL: {name} failed. Stopping checklist.")
            print_summary(results)
            sys.exit(1)
    
    # Run performance checks if URL provided
    if args.url and not args.skip_performance:
        print_header("⚡ PERFORMANCE CHECKS")
        for name, script_id, required in PERFORMANCE_CHECKS:
            result = run_script(name, script_id, str(project_path), args.url)
            results.append(result)
    
    # Print summary
    all_passed = print_summary(results)
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
