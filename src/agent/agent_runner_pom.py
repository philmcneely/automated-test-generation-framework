import argparse
import json
import re


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def to_snake_case(name):
    """Convert camelCase or TitleCase to snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_pom_playwright_test(ticket, kb):
    """Generate async POM-based Playwright test compatible with existing
    framework"""
    title = ticket.get('title', 'generated_test')
    steps = ticket.get('acceptance_criteria', [])
    
    # Build selector index from KB
    selector_index = {}
    page_objects = {}
    for po in kb.get('page_objects', []):
        page_name = po.get('name', 'UnknownPage')
        page_objects[page_name] = po
        for sel in po.get('selectors', []):
            selector_index[sel.get('element')] = {
                'selector': sel.get('selector'),
                'page': page_name
            }

    def resolve_target(t):
        """Resolve target to page object and selector"""
        if not t:
            return None, None
        if (t.startswith('#') or t.startswith('.') or t.startswith('[') or
                t.startswith('text=') or t.startswith('//')):
            return None, t  # Raw selector
        if t in selector_index:
            return selector_index[t]['page'], selector_index[t]['selector']
        return None, t

    # Generate test steps
    test_steps = []
    current_page = None
    
    for i, step in enumerate(steps):
        action = str(step.get('action', '')).lower()
        target = step.get('target')
        value = step.get('value')
        
        page_name, selector = resolve_target(target)
        
        # Handle page navigation
        if page_name and page_name != current_page:
            test_steps.append(
                f"    await app.{to_snake_case(page_name)}.navigate()"
            )
            current_page = page_name
        
        # Generate action-specific code with mapping to existing framework
        # methods
        if action == 'click' and selector:
            if page_name:
                # Map to existing framework method names
                if target == 'login_button':
                    test_steps.append(
                        f"    await app.{to_snake_case(page_name)}.click_login()"
                    )
                else:
                    # Fallback to generic method name
                    method_name = f"click_{to_snake_case(target)}"
                    test_steps.append(
                        f"    await app.{to_snake_case(page_name)}."
                        f"{method_name}()"
                    )
            else:
                # Use direct page interaction
                test_steps.append(f"    await page.click('{selector}')")
                
        elif action == 'fill' and selector is not None:
            if page_name:
                # Map to existing framework method names
                if target == 'username_field':
                    test_steps.append(
                        f"    await app.{to_snake_case(page_name)}."
                        f"enter_username('{str(value or '')}')"
                    )
                elif target == 'password_field':
                    test_steps.append(
                        f"    await app.{to_snake_case(page_name)}."
                        f"enter_password('{str(value or '')}')"
                    )
                else:
                    # Fallback to generic method name
                    method_name = f"enter_{to_snake_case(target)}"
                    test_steps.append(
                        f"    await app.{to_snake_case(page_name)}."
                        f"{method_name}('{str(value or '')}')"
                    )
            else:
                # Use direct page interaction
                test_steps.append(
                    f"    await page.fill('{selector}', "
                    f"'{str(value or '')}')"
                )
                
        elif action == 'goto' and selector:
            test_steps.append(f"    await page.goto('{selector}')")
            current_page = None  # Reset current page after navigation
            
        elif action == 'assert_text' and value:
            if page_name:
                # Use direct page assertion for text verification
                test_steps.append(
                    f"    await expect(page.locator('text="
                    f"{str(value)}')).to_be_visible()"
                )
            else:
                # Use direct page assertion
                test_steps.append(
                    f"    await expect(page.locator('text="
                    f"{str(value)}')).to_be_visible()"
                )
        else:
            test_steps.append(
                f"    # TODO: Unsupported step: {json.dumps(step)}"
            )

    # Generate test function name
    safe = ''.join([c.lower() if c.isalnum() else '_' for c in title])
    test_func_name = 'test_' + safe[:60].strip('_')

    # Generate the complete test code
    code_lines = [
        '"""',
        f'Generated test: {title}',
        'This test was automatically generated from Jira ticket '
        'acceptance criteria.',
        '"""',
        '',
        'import pytest',
        'from playwright.async_api import expect',
        '',
        '@pytest.mark.asyncio',
        '@pytest.mark.generated',
        f'async def {test_func_name}(page, app):',
        '    """',
        f'    {title}',
        '    """',
        ''
    ]
    
    code_lines.extend(test_steps)
    
    return '\n'.join(code_lines)


def main():
    parser = argparse.ArgumentParser(
        description='Generate POM-based Playwright test from ticket JSON and '
                    'KB JSON.'
    )
    parser.add_argument('--ticket', required=True,
                        help='Path to ticket JSON file')
    parser.add_argument('--kb', required=True,
                        help='Path to knowledge base JSON file')
    parser.add_argument('--output', help='Output file path (optional)')
    args = parser.parse_args()

    ticket = load_json(args.ticket)
    kb = load_json(args.kb)
    
    generated_test = generate_pom_playwright_test(ticket, kb)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(generated_test)
        print(f'Generated test saved to: {args.output}')
    else:
        print('# ===== Generated POM-based Playwright Test =====')
        print(generated_test)


if __name__ == '__main__':
    main()
