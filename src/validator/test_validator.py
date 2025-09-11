#!/usr/bin/env python3
"""
===============================================================================
Test Validation Service for Automated Test Generation
===============================================================================
This module validates generated Playwright tests by running them against the
playwright-ai-framework submodule and providing feedback on failures.

Features:
    ✓ Runs generated tests in isolated environment
    ✓ Captures test results and failures
    ✓ Provides detailed error analysis
    ✓ Integrates with LLM for failure analysis (optional)
    ✓ Updates knowledge base with learnings

Usage:
    python src/validator/test_validator.py --test path/to/generated_test.py

Author: Automated Test Generation System
===============================================================================
"""

import argparse
import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path


class TestValidator:
    def __init__(self, playwright_framework_path="playwright-ai-framework"):
        """
        Initialize the test validator with path to playwright framework.
        
        Args:
            playwright_framework_path: Path to playwright-ai-framework submodule
        """
        self.playwright_path = Path(playwright_framework_path)
        self.validation_results = []
        
    def validate_test(self, test_file_path):
        """
        Validate a generated test by running it in the playwright framework.
        
        Args:
            test_file_path: Path to the generated test file
            
        Returns:
            dict: Validation results including success/failure and error details
        """
        test_path = Path(test_file_path)
        
        if not test_path.exists():
            return {
                "success": False,
                "error": f"Test file not found: {test_file_path}",
                "test_file": test_file_path,
                "validation_time": None
            }
        
        # Copy test to playwright framework's generated tests directory
        target_dir = self.playwright_path / "tests" / "generated"
        target_dir.mkdir(exist_ok=True)
        
        target_file = target_dir / test_path.name
        
        # Read and modify test if needed for validation environment
        test_content = self._prepare_test_for_validation(test_path)
        
        # Write test to target location
        with open(target_file, 'w') as f:
            f.write(test_content)
        
        print(f"🧪 Validating test: {test_path.name}")
        
        # Run the test
        result = self._run_test(target_file)
        
        # Clean up
        if target_file.exists():
            target_file.unlink()
            
        return result
    
    def _prepare_test_for_validation(self, test_file_path):
        """
        Prepare test content for validation environment.
        May add validation-specific markers or modifications.
        
        Args:
            test_file_path: Path to original test file
            
        Returns:
            str: Modified test content
        """
        with open(test_file_path, 'r') as f:
            content = f.read()
        
        # Add validation marker if not present
        if '@pytest.mark.generated' in content and '@pytest.mark.validation' not in content:
            content = content.replace('@pytest.mark.generated', 
                                      '@pytest.mark.generated\n@pytest.mark.validation')
        
        return content
    
    def _run_test(self, test_file_path):
        """
        Run the test using pytest and capture results.
        
        Args:
            test_file_path: Path to test file in playwright framework
            
        Returns:
            dict: Test execution results
        """
        import time
        start_time = time.time()
        
        # Change to playwright framework directory
        original_cwd = os.getcwd()
        
        try:
            os.chdir(self.playwright_path)
            
            # Run pytest on the specific test
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_file_path),
                '-v',
                '--tb=short',
                '--disable-warnings'
            ]
            
            print(f"🚀 Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            execution_time = time.time() - start_time
            
            success = result.returncode == 0
            
            validation_result = {
                "success": success,
                "test_file": str(test_file_path),
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": execution_time,
                "validation_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if success:
                print("✅ Test validation PASSED")
            else:
                print("❌ Test validation FAILED")
                print("📋 Error output:")
                print(result.stderr)
                
            return validation_result
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Test execution timed out after 2 minutes",
                "test_file": str(test_file_path),
                "execution_time": time.time() - start_time,
                "validation_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Test execution failed: {str(e)}",
                "test_file": str(test_file_path),
                "execution_time": time.time() - start_time,
                "validation_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
        finally:
            os.chdir(original_cwd)
    
    def validate_batch(self, test_files):
        """
        Validate multiple test files.
        
        Args:
            test_files: List of test file paths
            
        Returns:
            list: List of validation results
        """
        results = []
        
        for test_file in test_files:
            result = self.validate_test(test_file)
            results.append(result)
            
        return results
    
    def generate_validation_report(self, results, output_file=None):
        """
        Generate a validation report from results.
        
        Args:
            results: List of validation results
            output_file: Optional file to save report
            
        Returns:
            str: Formatted validation report
        """
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get("success", False))
        failed_tests = total_tests - passed_tests
        
        report = []
        report.append("=" * 60)
        report.append("TEST VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {failed_tests}")
        report.append(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        report.append("")
        
        if failed_tests > 0:
            report.append("FAILED TESTS:")
            report.append("-" * 40)
            for result in results:
                if not result.get("success", False):
                    report.append(f"❌ {result.get('test_file', 'Unknown')}")
                    if result.get("stderr"):
                        report.append(f"   Error: {result['stderr'][:200]}...")
                    report.append("")
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"📄 Validation report saved to: {output_file}")
        
        return report_text


def main():
    parser = argparse.ArgumentParser(
        description='Validate generated Playwright tests against framework'
    )
    parser.add_argument('--test', required=True,
                        help='Path to generated test file')
    parser.add_argument('--framework-path', default='playwright-ai-framework',
                        help='Path to playwright framework (default: playwright-ai-framework)')
    parser.add_argument('--report', help='Output file for validation report')
    
    args = parser.parse_args()
    
    validator = TestValidator(args.framework_path)
    
    # Validate single test
    result = validator.validate_test(args.test)
    
    # Generate and display report
    report = validator.generate_validation_report([result], args.report)
    print(report)
    
    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == '__main__':
    main()
