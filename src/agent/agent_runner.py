import argparse
import json
import os

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def generate_playwright_test(ticket, kb):
    title = ticket.get('title', 'generated_test')
    steps = ticket.get('acceptance_criteria', [])
    # Build selector index from KB
    selector_index = {}
    for po in kb.get('page_objects', []):
        for sel in po.get('selectors', []):
            selector_index[sel.get('element')] = sel.get('selector')

    def resolve_target(t):
        if not t:
            return t
        if t.startswith('#') or t.startswith('.') or t.startswith('[') or t.startswith('text=') or t.startswith('//'):
            return t
        return selector_index.get(t, t)

    body_lines = []
    for s in steps:
        action = str(s.get('action', '')).lower()
        target = resolve_target(s.get('target'))
        value = s.get('value')
        if action == 'click' and target:
            body_lines.append(f"        page.click('{target}')")
        elif action == 'fill' and target is not None:
            body_lines.append(f"        page.fill('{target}', '{str(value or '')}')")
        elif action == 'goto' and target:
            body_lines.append(f"        page.goto('{target}')")
        elif action == 'assert_text' and value:
            body_lines.append(f"        page.wait_for_selector('text={str(value)}')")
        else:
            body_lines.append(f"        # TODO: Unsupported step: {json.dumps(s)}")

    base_url = os.getenv('APP_BASE_URL', 'https://example.com')
    safe = ''.join([c.lower() if c.isalnum() else '_' for c in title])
    test_func_name = 'test_' + safe[:60].strip('_')

    code_lines = [
        'import os',
        'import pytest',
        'from playwright.sync_api import sync_playwright',
        '',
        f'BASE_URL = os.getenv("APP_BASE_URL", "{base_url}")',
        '',
        '@pytest.mark.e2e',
        f'def {test_func_name}():',
        '    with sync_playwright() as p:',
        '        browser = p.chromium.launch(headless=True)',
        '        page = browser.new_page()',
        '        page.goto(BASE_URL)'
    ]
    
    code_lines.extend(body_lines)
    code_lines.append('        browser.close()')
    
    return '\n'.join(code_lines)

def main():
    parser = argparse.ArgumentParser(description='Generate a Playwright test from a ticket JSON and KB JSON.')
    parser.add_argument('--ticket', required=True)
    parser.add_argument('--kb', required=True)
    args = parser.parse_args()

    ticket = load_json(args.ticket)
    kb = load_json(args.kb)
    print('# ===== Generated Playwright Test =====')
    print(generate_playwright_test(ticket, kb))

if __name__ == '__main__':
    main()
