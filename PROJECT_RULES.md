# Project Rules - Automated Test Generation Framework

## � CRITICAL PROJECT RULES

### Rule 1: NEVER Commit Submodule Changes
- The `playwright-ai-framework/` directory is a git submodule
- **NEVER** commit changes to this submodule in this repository
- Always check git status before committing
- Use `git submodule update --init --recursive` to reset if needed
- The submodule is for test execution only, not development

### Rule 2: GitHub CLI Command Handling
- **NEVER** run `gh` commands directly in terminal
- **ALWAYS** pipe GitHub CLI results to a text file first
- Read the results from the file to avoid terminal breakage
- Example:
  ```bash
  # WRONG: gh repo view
  # CORRECT: gh repo view > gh_output.txt && cat gh_output.txt
  ```
- This prevents terminal session corruption from GitHub CLI output

### Rule 3: Directory Structure Integrity
```bash
# Before any commit, reset the submodule to prevent accidental inclusion
git submodule update --init --recursive
git checkout HEAD -- playwright-ai-framework
```

### Rule 4: Vector Database Files
- **NEVER** commit vector database files or embeddings
- Common patterns to avoid: `*.db`, `*.sqlite`, `*.vectordb`, `*.faiss`, `chroma_db/`, `embeddings/`
- These files are large and contain computed data that should be regenerated
- Always add to .gitignore if new vector storage systems are introduced

**RULE #5: Git Status Checking**
- Always check `git status` before committing
- If you see `modified: playwright-ai-framework (modified content)`, do NOT add it
- Use `git add -A` sparingly - prefer specific file additions

### Development Workflow Rules

**RULE #6: Class-Based Architecture Only**
- All new modules must be class-based, not functional
- Existing functional modules should be converted to classes when touched
- Use proper dependency injection for testability

**RULE #7: Comprehensive Testing Required**
- Every class must have a corresponding test file
- Aim for high test coverage with meaningful assertions
- Use proper mocking for external dependencies

**RULE #8: Type Annotations Mandatory**
- All functions and methods must have proper type annotations
- Use `typing` module for complex types
- Ensure mypy compliance

### Directory Structure Rules

**RULE #7: Directory Purpose Clarity**
- `/tests/` - Unit and integration tests for framework components only
- `/examples/` - Sample generated tests and templates only
- `/playwright-ai-framework/tests/` - Live E2E test execution environment only
- Never mix purposes between these directories

**RULE #8: Documentation Consistency**
- Keep all documentation references consistent with actual directory structure
- Update all affected files when making structural changes
- Maintain accuracy in feature descriptions

### Code Quality Rules

**RULE #9: Pre-commit Hooks Must Pass**
- All commits must pass black, flake8, mypy, bandit, safety checks
- No exceptions for formatting or linting issues
- Fix issues, don't suppress them

**RULE #10: Commit Message Standards**
- Use conventional commit format: `type: description`
- Be specific about what changed and why
- Reference issues/tickets when applicable

**RULE #11: Refactoring Standards**
- When refactoring modules, update ALL related files simultaneously:
  - Source code files
  - Test files
  - Documentation (README, IMPLEMENTATION_STATUS, etc.)
  - Import statements in other modules
  - CI/CD pipeline references
- Never leave broken imports or outdated references
- Test the entire pipeline after refactoring changes

**RULE #12: File Headers Required**
- ALL Python files (src/, tests/) must have standardized headers
- Header format must include:
  - Module purpose and description
  - Key features/functionality
  - Usage examples (where applicable)
  - Dependencies
  - Author, Date, Version
- Keep headers consistent across the project
- Update headers when refactoring or making significant changes

## 🔍 Enforcement

These rules are enforced by:
- Pre-commit hooks for code quality
- Manual review for submodule changes
- Documentation checks during code review
- Automated testing in CI/CD pipeline

## ⚠️ Violations

Violations of these rules, especially submodule commit rules, can cause:
- Repository history pollution
- Merge conflicts with submodule updates
- Loss of work in the submodule repository
- CI/CD pipeline failures
- Team confusion and wasted time

## 📝 Updates

This document should be updated when:
- New critical rules are identified
- Existing rules need clarification
- Workflow changes require rule modifications
- Tools or processes change significantly

Last updated: 2025-09-11
