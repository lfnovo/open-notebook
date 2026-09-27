"""Regression tests that execute the real selector JavaScript in a real Chrome.

These exist because the fake page layer returns canned values for `evaluate`, which
made two false positives in `research_selected` invisible to the rest of the suite.
Only local synthetic HTML is loaded here: no provider is contacted, no profile is used,
and headless is fine because nothing is being authenticated.
"""
from pathlib import Path
import sys
import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parents[1]))
from browser_research import BrowserResearch

COMPOSER = '<textarea></textarea>'

NOT_SELECTED = [
    ('Deep Think reasoning is not web Deep Research',
     '<form><button aria-pressed="true">Deep think</button>' + COMPOSER + '</form>'),
    ('unselected button inside the composer',
     '<form><button aria-pressed="false">Deep research</button>' + COMPOSER + '</form>'),
    ('selected control that is display:none',
     '<button aria-pressed="true" style="display:none">Deep research</button><form>' + COMPOSER + '</form>'),
    ('selected control that is visibility:hidden',
     '<button aria-pressed="true" style="visibility:hidden">Deep research</button><form>' + COMPOSER + '</form>'),
    ('bare label with no state and no remove control',
     '<form><span>Deep research</span>' + COMPOSER + '</form>'),
    ('explicit data-state off',
     '<form><button data-state="off">Deep research</button>' + COMPOSER + '</form>'),
    ('unchecked menu item',
     '<form><div role="menuitemradio" aria-checked="false">Deep research</div>' + COMPOSER + '</form>'),
    ('chip shaped element whose own control reports off',
     '<form><div class="chip"><button aria-pressed="false">Deep research</button>'
     '<button aria-label="Remove">x</button></div>' + COMPOSER + '</form>'),
    ('label lives outside the composer and carries no state',
     '<nav><span>Deep research</span></nav><form>' + COMPOSER + '</form>'),
    ('nothing resembling the control at all', '<form>' + COMPOSER + '</form>'),
]

SELECTED = [
    ('aria-pressed true', '<form><button aria-pressed="true">Deep research</button>' + COMPOSER + '</form>'),
    ('data-state on', '<form><button data-state="on">Deep research</button>' + COMPOSER + '</form>'),
    ('checked menu item',
     '<form><div role="menuitemradio" aria-checked="true">Derin araştırma</div>' + COMPOSER + '</form>'),
    ('composer chip with its own remove control',
     '<form><div class="chip"><span>Deep research</span>'
     '<button aria-label="Remove Deep research">x</button></div>' + COMPOSER + '</form>'),
    ('aria-label carries the mode name',
     '<form><button aria-pressed="true" aria-label="Deep research"><svg></svg></button>' + COMPOSER + '</form>'),
]


@pytest_asyncio.fixture(scope='module', loop_scope='module')
async def page():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True, chromium_sandbox=True)
        tab = await browser.new_page()
        yield tab
        await browser.close()


@pytest.fixture(scope='module')
def driver(tmp_path_factory):
    return BrowserResearch(None, tmp_path_factory.mktemp('dom'))


@pytest.mark.asyncio(loop_scope='module')
@pytest.mark.parametrize('name,html', NOT_SELECTED, ids=[n for n, _ in NOT_SELECTED])
async def test_research_mode_is_not_reported_as_selected(page, driver, name, html):
    await page.set_content(html)
    assert await driver.research_selected(page, 'ChatGPT') is False, name


@pytest.mark.asyncio(loop_scope='module')
@pytest.mark.parametrize('name,html', SELECTED, ids=[n for n, _ in SELECTED])
async def test_research_mode_is_recognised_when_genuinely_selected(page, driver, name, html):
    await page.set_content(html)
    assert await driver.research_selected(page, 'ChatGPT') is True, name


@pytest.mark.asyncio(loop_scope='module')
async def test_an_explicit_off_state_outranks_a_chip_shaped_sibling(page, driver):
    # A page can contain both. The provider's own "not selected" must win.
    await page.set_content(
        '<form><button aria-pressed="false">Deep research</button>'
        '<div class="chip"><span>Deep research</span><button aria-label="Remove">x</button></div>'
        + COMPOSER + '</form>')
    assert await driver.research_selected(page, 'ChatGPT') is False
