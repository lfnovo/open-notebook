'use client'

import { useState } from 'react'

const privacyPolicy =
  '本隐私政策适用于本网站所有访问用户、注册用户及服务使用者，访问、使用本网站即视为同意本政策全部条款。本站严格保护用户个人隐私，仅收集业务必要信息，用于服务对接与网站优化，不会非法泄露、出售用户信息，合理使用 Cookie 提升浏览体验，政策将不定期更新公示。'

const legalNotice =
  '本站所有内容版权归本企业所有，未经授权禁止商用转载。网站内容仅供参考，不构成专业建议，因第三方行为或自行使用产生的风险由用户自行承担，本站保留最终解释权。'

type LegalDialog = 'privacy' | 'legal' | null

export function HomeComplianceFooter() {
  const [openDialog, setOpenDialog] = useState<LegalDialog>(null)

  return (
    <footer className="border-t border-stone-200/60 bg-white px-6 py-8">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm font-semibold text-stone-500 sm:text-base">
        <span>© 2026 成都寅时智能</span>
        <button
          type="button"
          onClick={() => setOpenDialog('privacy')}
          className="transition-colors hover:text-stone-900"
        >
          隐私政策
        </button>
        <button
          type="button"
          onClick={() => setOpenDialog('legal')}
          className="transition-colors hover:text-stone-900"
        >
          法律声明
        </button>
        <a
          href="https://beian.miit.gov.cn/"
          target="_blank"
          rel="noreferrer"
          className="transition-colors hover:text-stone-900"
        >
          蜀ICP备2026017298号
        </a>
        <a
          href="https://beian.mps.gov.cn/#/query/webSearch?code=51019002009363"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 transition-colors hover:text-stone-900"
        >
          {/* Official public-security filing badge is served by beian.gov.cn. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://www.beian.gov.cn/img/ghs.png"
            alt="公安徽标"
            className="h-5 w-5 object-contain"
            referrerPolicy="no-referrer"
          />
          川公网安备51019002009363号
        </a>
      </div>

      {openDialog ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/55 px-6 backdrop-blur-sm"
          role="presentation"
          onClick={() => setOpenDialog(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="home-compliance-dialog-title"
            className="w-full max-w-lg rounded-2xl bg-white p-7 shadow-2xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h2
              id="home-compliance-dialog-title"
              className="mb-4 text-xl font-bold text-stone-900"
            >
              {openDialog === 'privacy' ? '隐私政策' : '法律声明'}
            </h2>
            <p className="text-sm leading-7 text-stone-600 sm:text-base">
              {openDialog === 'privacy' ? privacyPolicy : legalNotice}
            </p>
            <div className="mt-7 flex justify-end">
              <button
                type="button"
                onClick={() => setOpenDialog(null)}
                className="rounded-full bg-stone-900 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-stone-700"
              >
                我知道了
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </footer>
  )
}
