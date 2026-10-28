"""Verify Studio settings and capture public-safe screens.

Usage: python scripts/capture_studio.py --url http://127.0.0.1:8799 --out build/studio
Requires Playwright and Edge. Run against a Studio with a TEMPORARY config path;
this workflow saves reset_warning_s=3600 and never uses real service settings.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--url', required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url)
        page.wait_for_load_state('networkidle')
        page.wait_for_function("document.querySelector('#profile').options.length > 0")
        page.locator('[data-tab="settings"]').click()
        expect(page.locator('#cfg_serial_port')).to_have_value('auto')
        expect(page.locator('#save')).not_to_be_visible()
        page.locator('#cfg_reset_warning_s').fill('1800')
        expect(page.locator('#settingsDirty')).to_have_class('dirty on')
        page.once('dialog', lambda dialog: dialog.dismiss())
        page.locator('[data-tab="layout"]').click()
        expect(page.locator('#tab-settings')).to_have_class('tab on')
        page.locator('#settingsRevert').click()
        expect(page.locator('#cfg_reset_warning_s')).to_have_value('3600')
        page.locator('#settingsSave').click()
        expect(page.locator('#settingsNotice')).to_contain_text('Restart')
        page.reload()
        page.wait_for_function("document.querySelector('#profile').options.length > 0")
        page.locator('[data-tab="settings"]').click()
        expect(page.locator('#cfg_reset_warning_s')).to_have_value('3600')
        page.screenshot(path=str(args.out / 'studio-settings.png'), full_page=True, animations='disabled')
        page.locator('[data-tab="library"]').click()
        page.evaluate("openViewer(state.library.find(e => e.id === 'plasma'), true)")
        expect(page.locator('#editor')).to_be_visible()
        expect(page.locator('#eSkyWrap')).not_to_be_visible()
        expect(page.locator('#eGen h3')).to_contain_text('Plasma')
        page.locator('#eGen').scroll_into_view_if_needed()
        page.locator('#viewer .sheet').screenshot(path=str(args.out / 'studio-generator.png'), animations='disabled')
        page.locator('#viewer [data-close]').click()
        page.evaluate("openViewer(state.library.find(e => e.id === 'miami-drive'), true)")
        expect(page.locator('#eSkyWrap')).to_be_visible()
        page.locator('#viewer [data-close]').click()
        page.set_viewport_size({'width': 900, 'height': 1000})
        page.locator('[data-tab="settings"]').click()
        page.screenshot(path=str(args.out / 'studio-settings-narrow.png'), full_page=True, animations='disabled')
        if errors:
            raise RuntimeError('Browser errors: ' + '; '.join(errors))
        browser.close()
    print('PASS: settings save/reload, dirty/revert/navigation, generator/image sky visibility; no browser errors')


if __name__ == '__main__':
    main()
