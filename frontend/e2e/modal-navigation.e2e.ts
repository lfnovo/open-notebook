import type { Page, Route } from '@playwright/test'
import { test, expect, notebookPath, source, note, insight } from './fixtures'

const modals = [
  { type: 'source', id: source.id, name: 'Source Details' },
  { type: 'note', id: note.id, name: 'Edit note' },
  { type: 'insight', id: insight.id, name: /Source Insight/ },
] as const

type Modal = typeof modals[number]

function modalUrl(modal: Modal, suffix = '') {
  return `${notebookPath}?modal=${modal.type}&id=${encodeURIComponent(modal.id)}${suffix}`
}

async function expectModal(page: Page, modal: Modal) {
  const dialog = page.getByRole('dialog', { name: modal.name, exact: true })
  await expect(dialog).toBeVisible()
  if (modal.type === 'note') {
    await expect(dialog.locator('#note-content')).toHaveValue(note.content)
  } else {
    await expect(dialog.getByText(modal.type === 'source' ? source.full_text : insight.content, { exact: true })).toBeVisible()
  }
  return dialog
}

async function expectClosed(page: Page, url: string) {
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.locator('[data-slot="dialog-overlay"]')).toHaveCount(0)
  await expect(page).toHaveURL(url)
  // Radix must also release the page's pointer and focus restrictions.
  await page.getByRole('link', { name: 'Notebooks', exact: true }).click({ trial: true })
}

async function blockModalNavigation(page: Page) {
  const pending: Route[] = []
  const handler = async (route: Route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.headers()['rsc'] === '1' &&
        decodeURIComponent(url.pathname) === notebookPath && !url.searchParams.has('modal')) {
      // Leave the navigation unresolved until assertions complete. A router.push
      // based close must fail here even if the server normally responds quickly.
      pending.push(route)
      return
    }
    await route.fallback()
  }
  await page.route('**/*', handler)
  return async () => {
    await page.unroute('**/*', handler)
    await Promise.all(pending.map(route => route.abort()))
  }
}

// #1399: a hard-loaded modal must remain dismissible while RSC navigation stalls.
for (const modal of modals) {
  for (const action of ['Close', 'Escape'] as const) {
    for (const suffix of ['', '&keep=one&keep=two#section']) {
      test(`${modal.type} closes with ${action} after refresh and supports Back/Forward (${suffix ? 'query and hash' : 'no other params'})`, async ({ page }) => {
        const openUrl = modalUrl(modal, suffix)
        const closedUrl = suffix ? `${notebookPath}?keep=one&keep=two#section` : notebookPath
        await page.goto(openUrl)
        await expectModal(page, modal)
        await page.reload()
        const dialog = await expectModal(page, modal)
        const unblock = await blockModalNavigation(page)
        try {
          if (action === 'Close') await dialog.getByRole('button', { name: 'Close', exact: true }).click()
          else await page.keyboard.press('Escape')
          await expectClosed(page, closedUrl)

          await page.goBack()
          await expect(page).toHaveURL(openUrl)
          await expectModal(page, modal)
          await page.goForward()
          await expectClosed(page, closedUrl)
        } finally {
          await unblock()
        }
      })
    }
  }
}

test('a source dialog can still navigate to the full source chat page', async ({ page }) => {
  await page.goto(modalUrl(modals[0]))
  const dialog = await expectModal(page, modals[0])
  await dialog.getByRole('button', { name: 'Chat with Sources', exact: true }).click()
  await expect.poll(() => decodeURIComponent(new URL(page.url()).pathname)).toBe(`/sources/${source.id}`)
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByText(source.full_text, { exact: true })).toBeVisible()
})

test('an insight reference and its source can be revisited with Back and Forward', async ({ page }) => {
  await page.goto(modalUrl(modals[2]))
  const insightDialog = await expectModal(page, modals[2])
  await insightDialog.getByRole('button', { name: 'View Source', exact: true }).click()
  const sourceDialog = await expectModal(page, modals[0])
  await sourceDialog.getByRole('button', { name: 'Close', exact: true }).click()
  await expectClosed(page, notebookPath)

  await page.goBack()
  await expectModal(page, modals[0])
  await page.goBack()
  await expectModal(page, modals[2])
  await page.goForward()
  await expectModal(page, modals[0])
  await page.goForward()
  await expectClosed(page, notebookPath)
})
