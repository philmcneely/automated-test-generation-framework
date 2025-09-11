#!/bin/bash
# Script to properly remove embedded playwright-ai-framework and set up as submodule

echo "🔄 Removing embedded playwright-ai-framework directory..."
echo "📋 This script will help you transition from embedded to submodule approach"

# Step 1: Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not in a git repository. Please initialize git first:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Step 2: Remove the embedded directory safely
echo "🗑️  Removing embedded playwright-ai-framework directory..."
if [ -d "playwright-ai-framework" ]; then
    # Move to temp location first (safer than direct deletion)
    mv playwright-ai-framework /tmp/playwright-ai-framework-backup
    echo "✅ Moved embedded directory to /tmp/playwright-ai-framework-backup"
else
    echo "⚠️  playwright-ai-framework directory not found"
fi

# Step 3: Initialize the submodule
echo "📦 Initializing git submodule..."
git submodule add https://github.com/philmcneely/playwright-ai-framework.git playwright-ai-framework
git submodule update --init --recursive

# Step 4: Configure submodule
echo "⚙️  Configuring submodule..."
git config -f .gitmodules submodule.playwright-ai-framework.branch main

# Step 5: Test the setup
echo "🧪 Testing submodule integration..."
cd playwright-ai-framework
if [ -f "conftest.py" ]; then
    echo "✅ Submodule successfully initialized - framework files found"
else
    echo "❌ Submodule may not have initialized correctly"
fi
cd ..

echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Test the validation: python src/validator/test_validator.py --test playwright-ai-framework/tests/generated/test_generated_login_fixed.py"
echo "2. Run the poller: python src/poller/jira_poller_with_validation.py"
echo "3. Commit changes: git add .gitmodules && git commit -m 'Add playwright-ai-framework as submodule'"
echo ""
echo "💡 To update the submodule later: git submodule update --remote"
