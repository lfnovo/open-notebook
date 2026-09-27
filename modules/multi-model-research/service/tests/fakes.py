"""A minimal stand-in for the Playwright surface browser_research.py actually uses.

Elements are plain dicts. `sel` lists selector fragments the element answers to, so a
test can register a node for '[data-message-author-role="assistant"]' without a DOM.

This fake exercises the *flow* around the selectors; it deliberately does not run the
selector JavaScript. That JavaScript is covered against a real Chrome DOM in
tests/test_dom.py, because canned `evaluate` results once hid two false positives here.
The shapes returned below must mirror what the real JS returns.
"""
from __future__ import annotations
import json


def el(sel=(), role=None, name=None, text='', html=None, visible=True, enabled=True, on_click=None):
    return {'sel': list(sel), 'role': role, 'name': name, 'text': text,
            'html': html if html is not None else '<p>' + text + '</p>',
            'visible': visible, 'enabled': enabled, 'on_click': on_click}


class Loc:
    def __init__(self, page, items):
        self.page = page
        self.items = items

    async def count(self):
        return len(self.items)

    def nth(self, i):
        return Loc(self.page, self.items[i:i + 1])

    @property
    def first(self):
        return Loc(self.page, self.items[:1])

    @property
    def last(self):
        return Loc(self.page, self.items[-1:])

    async def is_visible(self):
        return bool(self.items) and self.items[0]['visible']

    async def is_enabled(self):
        return bool(self.items) and self.items[0]['enabled']

    async def click(self):
        if not self.items:
            raise AssertionError('click on empty locator')
        item = self.items[0]
        self.page.clicks.append(item.get('name') or (item['sel'][0] if item['sel'] else '?'))
        if item['on_click']:
            item['on_click'](self.page)

    async def inner_text(self):
        return self.items[0]['text'] if self.items else ''

    async def inner_html(self):
        return self.items[0]['html'] if self.items else ''

    async def all_text_contents(self):
        return [i['text'] for i in self.items]

    async def fill(self, value):
        self.page.filled.append(value)

    async def set_input_files(self, path):
        self.page.uploads.append(path)

    async def wait_for(self, **kwargs):
        if not self.items or not self.items[0]['visible']:
            raise TimeoutError('not visible')

    async def evaluate_all(self, js):
        if 'a.href' in js:
            return [i['name'] for i in self.items]
        return [{'title': i['text'], 'url': i['name']} for i in self.items]

    def locator(self, selector):
        return self.page.locator(selector)


class Keyboard:
    def __init__(self, page):
        self.page = page

    async def press(self, key):
        self.page.keys.append(key)


class FakePage:
    def __init__(self, url='https://chatgpt.com/', elements=None, title='ChatGPT',
                 selected_mode='', selected_negative=False, chip=False, nav_links=()):
        self.url = url
        self.elements = list(elements or [])
        self._title = title
        self.selected_mode = selected_mode
        self.selected_negative = selected_negative
        self.chip = chip
        self.nav_links = list(nav_links)
        self.clicks = []
        self.filled = []
        self.uploads = []
        self.keys = []
        self.gotos = []
        self.closed = False
        self.keyboard = Keyboard(self)

    # -- test helpers
    def add(self, element):
        self.elements.append(element)
        return element

    def is_closed(self):
        return self.closed

    async def title(self):
        return self._title

    async def goto(self, url, **kwargs):
        self.gotos.append(url)
        self.url = url

    async def bring_to_front(self):
        pass

    async def close(self):
        self.closed = True

    async def wait_for_timeout(self, ms):
        pass

    def locator(self, selector):
        hits = [e for e in self.elements if any(s in selector for s in e['sel'])]
        return Loc(self, hits)

    def get_by_role(self, role, name=None, exact=False):
        hits = [e for e in self.elements
                if e['role'] == role and (name is None or e['name'] == name)]
        return Loc(self, hits)

    def get_by_text(self, text, exact=False):
        hits = [e for e in self.elements if text in (e['text'] or '')]
        return Loc(self, hits)

    async def evaluate(self, js, arg=None):
        if "JSON.stringify({positive:positive,negative:negative})" in js:
            # Same contract as SELECTED_JS in browser_research.py.
            return json.dumps({'positive': self.selected_mode, 'negative': self.selected_negative})
        if 'const labels=args[0],scope=args[1]' in js:
            return self.chip
        if 'a.href' in js:
            return list(self.nav_links)
        return []


class FakeRuntime:
    """Only what BrowserResearch calls. Never touches a real browser."""

    def __init__(self, page, research_entry=None, check_error=None):
        self.page_obj = page
        self.entry = research_entry
        self.check_error = check_error
        self.checks = 0
        self.released = []

    async def page(self, key, provider, url=None):
        return self.page_obj

    async def check(self, page, provider):
        self.checks += 1
        if self.check_error:
            raise self.check_error

    async def research_entry(self, page, provider):
        return self.entry

    async def release(self, key):
        self.released.append(key)

    async def close(self):
        pass
