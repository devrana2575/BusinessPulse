#!/usr/bin/env python3
"""Unified test runner for BusinessPulse.

Runs all unit tests, data pipeline tests, and Power BI project validation tests
in the offline environment.
"""

import sys
import os
import inspect
import tempfile
import shutil
import re
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Mock database drivers if missing in offline sandbox
for mod in ["sqlalchemy", "sqlalchemy.engine", "sqlalchemy.exc", "pymysql", "dotenv"]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import pytest
import tests.conftest as conftest

def run_function_test(func, kwargs):
    sig = inspect.signature(func)
    call_kwargs = {}
    temp_dir = None
    if "tmp_path" in sig.parameters:
        temp_dir = tempfile.mkdtemp()
        call_kwargs["tmp_path"] = Path(temp_dir)
    for p in sig.parameters:
        if p in kwargs:
            call_kwargs[p] = kwargs[p]
    try:
        if hasattr(func, "__parametrize__"):
            argnames, argvalues = func.__parametrize__
            if isinstance(argnames, str):
                argnames = [a.strip() for a in argnames.split(",")]
            for val in argvalues:
                step_kwargs = dict(call_kwargs)
                if len(argnames) == 1:
                    step_kwargs[argnames[0]] = val
                else:
                    for aname, aval in zip(argnames, val):
                        step_kwargs[aname] = aval
                func(**step_kwargs)
        else:
            func(**call_kwargs)
        return True, None
    except Exception as e:
        return False, e
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def run_method_test(instance, method, kwargs):
    sig = inspect.signature(method)
    call_kwargs = {}
    temp_dir = None
    if "tmp_path" in sig.parameters:
        temp_dir = tempfile.mkdtemp()
        call_kwargs["tmp_path"] = Path(temp_dir)
    for p in sig.parameters:
        if p in kwargs:
            call_kwargs[p] = kwargs[p]
    try:
        if hasattr(method, "__parametrize__"):
            argnames, argvalues = method.__parametrize__
            if isinstance(argnames, str):
                argnames = [a.strip() for a in argnames.split(",")]
            for val in argvalues:
                step_kwargs = dict(call_kwargs)
                if len(argnames) == 1:
                    step_kwargs[argnames[0]] = val
                else:
                    for aname, aval in zip(argnames, val):
                        step_kwargs[aname] = aval
                method(**step_kwargs)
        else:
            method(**call_kwargs)
        return True, None
    except Exception as e:
        return False, e
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def run_all_tests():
    fixtures = {
        "raw_rows": conftest.raw_rows(),
        "valid_raw_df": conftest.valid_raw_df(conftest.raw_rows()),
        "cleaned_df": conftest.cleaned_df(conftest.valid_raw_df(conftest.raw_rows())),
    }

    test_modules = [
        ("tests.test_powerbi_project", "Power BI Project (PBIP/PBIR/TMDL) Tests"),
        ("tests.test_powerbi_desktop_project", "Power BI Desktop Star-Schema Tests"),
        ("tests.test_cleaning", "Data Cleaning and Normalization Tests"),
        ("tests.test_validation", "Validation Rules Tests"),
        ("tests.test_opportunity", "Opportunity Score Calculation Tests"),
        ("tests.test_assets", "Project Assets and DDL Tests"),
    ]

    total_passed = 0
    total_failed = 0
    total_skipped = 0

    print("======================================================================")
    print("                    BusinessPulse Test Suite                          ")
    print("======================================================================")

    for mod_name, desc in test_modules:
        print(f"\n--- {desc} ({mod_name}) ---")
        try:
            mod = __import__(mod_name, fromlist=["*"])
        except Exception as e:
            print(f"  [ERROR] Could not load module: {e}")
            total_failed += 1
            continue

        mod_passed = 0
        mod_failed = 0
        mod_skipped = 0

        # Functions
        for name, func in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            if getattr(func, "__mysql__", False):
                print(f"  [SKIP] {name} (requires live MySQL database)")
                mod_skipped += 1
                continue
            ok, err = run_function_test(func, fixtures)
            if ok:
                print(f"  [PASS] {name}")
                mod_passed += 1
            else:
                print(f"  [FAIL] {name}: {err}")
                mod_failed += 1

        # Classes
        for cls_name, cls in inspect.getmembers(mod, inspect.isclass):
            if not cls_name.startswith("Test"):
                continue
            try:
                inst = cls()
            except Exception as e:
                print(f"  [FAIL] Init {cls_name}: {e}")
                mod_failed += 1
                continue
            for name, method in inspect.getmembers(inst, inspect.ismethod):
                if not name.startswith("test_"):
                    continue
                if getattr(method, "__mysql__", False):
                    print(f"  [SKIP] {cls_name}.{name} (requires live MySQL database)")
                    mod_skipped += 1
                    continue
                ok, err = run_method_test(inst, method, fixtures)
                if ok:
                    print(f"  [PASS] {cls_name}.{name}")
                    mod_passed += 1
                else:
                    print(f"  [FAIL] {cls_name}.{name}: {err}")
                    mod_failed += 1

        print(f"Subtotal: {mod_passed} passed, {mod_failed} failed, {mod_skipped} skipped")
        total_passed += mod_passed
        total_failed += mod_failed
        total_skipped += mod_skipped

    print("\n======================================================================")
    print(f"FINAL TEST SUMMARY: {total_passed} PASSED, {total_failed} FAILED, {total_skipped} SKIPPED")
    print("======================================================================")
    return total_failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
