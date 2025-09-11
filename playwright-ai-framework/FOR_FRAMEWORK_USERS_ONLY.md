# Playwright AI Framework - For Framework-Only Users

## 🎯 **Important: This is a Pure Playwright Framework**
**You can use this framework completely independently of any test generation system.**
**No Jira integration, no AI test generation, no external dependencies - just a solid Playwright testing framework.**

## ✅ **What This Framework Provides**
- **Pure Playwright testing** with Python and pytest
- **Page Object Model** architecture
- **AI-powered test healing** (optional, can be disabled)
- **Visual regression testing**
- **Allure reporting**
- **BrowserStack integration**
- **Comprehensive test utilities**

## 🚫 **What You Won't Find Here**
- No Jira integration code
- No automated test generation
- No external dependencies beyond what's needed for testing
- No knowledge of any test generation system

## 🚀 **Getting Started (Framework Only)**

### 1. Clone and Setup
```bash
# Clone the framework
git clone https://github.com/philmcneely/playwright-ai-framework.git
cd playwright-ai-framework

# Install dependencies
pip install -r requirements_with_versions.txt

# Install Playwright browsers
python -m playwright install chromium

# Set up environment variables (copy from .env.example)
cp .env.example .env.dev
# Edit .env.dev with your configuration
```

### 2. Run Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/login/ -v                    # Login tests
python -m pytest tests/test_smoke.py -v            # Smoke tests
python -m pytest tests/test_visual.py -v           # Visual tests

# Run with specific browser
BROWSER=firefox python -m pytest tests/ -v

# Run with AI healing disabled
AI_HEALING_ENABLED=false python -m pytest tests/ -v
```

### 3. Generate Reports
```bash
# Run tests with Allure reporting
python -m pytest tests/ --alluredir=test_artifacts/allure/allure-results

# Generate Allure report
allure generate test_artifacts/allure/allure-results -o test_artifacts/allure/allure-report --clean

# View report
open test_artifacts/allure/allure-report/index.html  # macOS
xdg-open test_artifacts/allure/allure-report/index.html  # Linux
```

## 📁 **Directory Structure (What You'll Actually Use)**
```
playwright-ai-framework/
├── tests/                    # Your test files
│   ├── login/               # Login-related tests
│   ├── api/                 # API tests
│   ├── visual_regression/   # Visual regression tests
│   └── generated/           # Empty directory (ignore this)
├── pages/                   # Page Object Models
│   ├── login_page.py        # Login page methods
│   ├── secure_page.py       # Secure area methods
│   └── base_page.py         # Base page functionality
├── utils/                   # Testing utilities
│   ├── ai_healing.py        # AI healing (optional)
│   ├── visual_regression.py # Visual testing
│   └── network_mocking.py   # API mocking
├── conftest.py              # Test configuration
└── pytest.ini              # Pytest settings
```

## 🔧 **Configuration Options**

### Environment Variables
```bash
# Basic configuration
BASE_URL=https://the-internet.herokuapp.com
BROWSER=chromium              # chromium, firefox, webkit
HEADLESS=true                 # true or false

# AI Healing (optional - disable if not needed)
AI_HEALING_ENABLED=false      # Disable AI healing
OLLAMA_MODEL=llama3.1:8b      # AI model for healing

# BrowserStack (optional)
BROWSERSTACK_ENABLED=false
BROWSERSTACK_USERNAME=your_username
BROWSERSTACK_ACCESS_KEY=your_key

# Visual Testing (optional)
SKIP_SCREENSHOTS=false        # Enable visual testing
```

## 🎨 **Features You Can Use**

### 1. Page Object Model
```python
# Example test using Page Object Model
@pytest.mark.asyncio
async def test_login_flow(page, app):
    await app.login_page.navigate()
    await app.login_page.enter_username("tomsmith")
    await app.login_page.enter_password("SuperSecretPassword!")
    await app.login_page.click_login()
    assert await app.secure_page.is_on_secure_page()
```

### 2. Visual Regression Testing
```python
# Visual regression test
@pytest.mark.asyncio
async def test_homepage_visual(page, visual_regression):
    await page.goto("https://example.com")
    await visual_regression("homepage", tolerance=0.02)
```

### 3. API Mocking
```python
# Mock API responses
@pytest.mark.asyncio
async def test_with_mocked_api(page, api_mocker):
    await api_mocker.mock_get("**/api/users", {"users": [{"id": 1}]})
    await page.goto("https://example.com")
    # Test with mocked data
```

### 4. AI Healing (Optional)
```bash
# Enable AI healing for automatic test fixing
AI_HEALING_ENABLED=true OLLAMA_MODEL=llama3.1:8b pytest tests/
```

## 🧪 **Test Categories Available**
- **Smoke Tests**: Basic functionality tests
- **Login Tests**: Authentication and authorization
- **Visual Tests**: Screenshot comparison testing
- **API Tests**: Network mocking and API testing
- **Performance Tests**: Load and performance monitoring
- **Security Tests**: Security vulnerability testing

## 📊 **Reporting Options**
- **Allure Reports**: Beautiful HTML test reports
- **Pytest Output**: Standard console output
- **CI/CD Integration**: Works with GitHub Actions, Jenkins, etc.

## 🔗 **Integration with CI/CD**
The framework works perfectly with:
- GitHub Actions
- Jenkins
- GitLab CI
- Azure DevOps
- Any CI/CD system that supports Python/pytest

## ❓ **Frequently Asked Questions**

**Q: What is the `tests/generated/` directory?**
**A:** It's an empty directory that can be safely ignored. It's only used if someone chooses to integrate automated test generation (which is completely optional).

**Q: Do I need to install any test generation dependencies?**
**A:** No! Just install the framework dependencies listed in `requirements_with_versions.txt`.

**Q: Can I delete the `tests/generated/` directory?**
**A:** You could, but it's better to leave it empty. It doesn't affect anything and keeps the structure consistent.

**Q: Will future updates to this framework add test generation dependencies?**
**A:** No! This framework will always remain pure and independent. Any test generation integration happens through completely separate tools/repositories.

## 🎯 **Bottom Line**
**This is a solid, independent Playwright testing framework.** 
- Use it exactly like any other testing framework
- Ignore anything related to test generation - that's completely separate
- All features work exactly as documented in the main README
- You get all the benefits (AI healing, visual testing, etc.) without any of the complexity

**Happy testing! 🚀**
