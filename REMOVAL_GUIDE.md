# Guide: Removing Embedded playwright-ai-framework Directory

## Overview
This guide explains how to properly remove the embedded `playwright-ai-framework` directory and transition to using it as a git submodule that points to your GitHub repository.

## Current State
You currently have:
- `playwright-ai-framework/` directory (embedded copy)
- `.gitmodules` file (configured to point to your GitHub repo)
- All the integration code working with the embedded copy

## Removal Steps

### Step 1: Backup the Current State (Optional but Recommended)
```bash
# Create a backup of the current embedded framework
cp -r playwright-ai-framework /tmp/playwright-ai-framework-backup
```

### Step 2: Remove the Embedded Directory
```bash
# Remove the embedded directory
rm -rf playwright-ai-framework
```

### Step 3: Initialize Git Repository (if not already done)
```bash
# Initialize git if you haven't already
git init
git add .
git commit -m "Initial commit before submodule setup"
```

### Step 4: Set Up the Submodule
```bash
# Add your GitHub repository as a submodule
git submodule add https://github.com/philmcneely/playwright-ai-framework.git playwright-ai-framework

# Initialize and update the submodule
git submodule update --init --recursive

# Configure the submodule to track the main branch
git config -f .gitmodules submodule.playwright-ai-framework.branch main
```

### Step 5: Verify the Setup
```bash
# Check that the submodule was set up correctly
ls -la playwright-ai-framework/
# Should show the framework files from your GitHub repo

# Test the validation system
python src/validator/test_validator.py --test examples/generated_test_login_happy_path.py
```

### Step 6: Commit the Changes
```bash
# Add the submodule configuration
git add .gitmodules
git add playwright-ai-framework

# Commit the changes
git commit -m "Replace embedded playwright-ai-framework with git submodule"
```

## What Changes After Removal

### Before Removal:
- Embedded copy of playwright-ai-framework in your directory
- Tests run against local embedded copy
- Manual synchronization with GitHub repo

### After Removal:
- Git submodule pointing to your GitHub repository
- Automatic synchronization with upstream changes
- Clean separation between projects
- Proper version control of the integration

## Benefits of This Approach

1. **Clean Separation**: Your test generation code is completely separate from the framework
2. **Version Control**: Framework updates are managed through git submodule
3. **No Code Conflicts**: Changes in either project don't affect the other
4. **Easy Updates**: `git submodule update --remote` to get latest framework changes
5. **Production Ready**: Suitable for enterprise deployment

## Testing the New Setup

After removal, test that everything still works:

```bash
# Test validation
python src/validator/test_validator.py --test playwright-ai-framework/tests/generated/test_generated_login_fixed.py

# Test poller with validation
python src/poller/jira_poller_with_validation.py

# Generate a new test
python src/agent/template_generator.py --ticket sample_ticket.json --kb knowledge_base_existing_framework.json --output test_new.py

# Validate the new test
python src/validator/test_validator.py --test test_new.py
```

## Troubleshooting

### If submodule doesn't initialize properly:
```bash
git submodule deinit -f playwright-ai-framework
git rm -f playwright-ai-framework
git submodule add https://github.com/philmcneely/playwright-ai-framework.git playwright-ai-framework
```

### If you need to recover from backup:
```bash
rm -rf playwright-ai-framework
cp -r /tmp/playwright-ai-framework-backup playwright-ai-framework
```

### To update the submodule later:
```bash
git submodule update --remote
```

## Summary
By removing the embedded directory and using the git submodule, you achieve:
- ✅ Complete separation between projects
- ✅ No more code conflicts or shared dependencies
- ✅ Independent CI/CD pipelines
- ✅ Clean, production-ready architecture
- ✅ Easy maintenance and updates

The submodule approach gives you all the benefits of separation while maintaining the integration capabilities you need.
