import Link from 'next/link'
import Image from 'next/image'
import { BookOpen, FileText, Brain, ArrowRight, Shield, Sparkles } from 'lucide-react'

export function HomePageContent() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 to-white">
      {/* Nav */}
      <header className="border-b border-stone-200/60 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-base text-stone-800">Lumina</span>
          </div>
          <div className="flex items-center gap-4">
            <Link
              href="/public"
              className="text-sm text-stone-600 hover:text-stone-900 transition-colors"
            >
              公开内容
            </Link>
            <Link
              href="/login"
              className="text-sm text-stone-600 hover:text-stone-900 transition-colors"
            >
              登录
            </Link>
            <Link
              href="/register"
              className="text-sm px-4 py-1.5 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors font-medium"
            >
              注册
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="px-6 py-10 sm:py-12">
        <HeroBrandSection />
      </div>

      {/* CTA */}
      <section className="py-12 sm:py-14 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mb-4">
            准备开始你的研究之旅？
          </h2>
          <p className="text-stone-500 text-lg mb-8 max-w-xl mx-auto">
            免费注册，即刻体验 AI 驱动的知识管理
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-slate-600 text-white hover:bg-slate-700 transition-colors text-base font-medium shadow-sm shadow-slate-300/60"
          >
            免费注册
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 sm:py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900">
              赋能你的研究工作流
            </h2>
            <p className="mt-3 text-stone-500 max-w-xl mx-auto">
              从资料收集到深度洞察，Lumina 让每一步都更高效
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard
              icon={<FileText className="w-5 h-5" />}
              title="多源资料整合"
              description="上传 PDF、网页、视频、音频等多种格式，统一管理和分析"
            />
            <FeatureCard
              icon={<Brain className="w-5 h-5" />}
              title="AI 深度分析"
              description="自动提取关键信息，生成摘要和洞察，发现隐藏的关联"
            />
            <FeatureCard
              icon={<BookOpen className="w-5 h-5" />}
              title="知识图谱"
              description="可视化知识结构，直观展示概念之间的关联与脉络"
            />
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="py-16 sm:py-20 px-6 bg-stone-50/50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl sm:text-3xl font-bold text-stone-900">
              适用场景
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <UseCaseCard
              title="学术研究"
              description="上传论文和文献，让 AI 帮你梳理研究脉络，发现新的研究方向"
            />
            <UseCaseCard
              title="产品调研"
              description="汇集竞品资料和市场数据，自动提炼关键洞察和趋势"
            />
            <UseCaseCard
              title="个人学习"
              description="整理课程笔记和学习材料，构建个性化的知识体系"
            />
            <UseCaseCard
              title="内容创作"
              description="以可靠来源为基础，辅助写作和研究性的内容产出"
            />
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section className="py-16 sm:py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary/10 mb-6">
            <Shield className="w-6 h-6 text-primary" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-stone-900 mb-4">
            你的数据，你做主
          </h2>
          <p className="text-stone-500 text-lg leading-relaxed max-w-xl mx-auto">
            Lumina 采用本地优先的架构设计。你的数据完全由你掌控，
            不会被用于训练任何 AI 模型。隐私是我们的核心承诺。
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-stone-200/60">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-primary/20 flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-primary" />
            </div>
            <span className="text-sm text-stone-400">Lumina by Yinshi AI</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-stone-400">
            <Link href="/login" className="hover:text-stone-600 transition-colors">
              登录
            </Link>
            <Link href="/register" className="hover:text-stone-600 transition-colors">
              注册
            </Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function HeroBrandSection() {
  return (
    <section
      className="relative mx-auto max-w-5xl overflow-hidden text-center"
      style={{
        aspectRatio: '2048 / 1099',
      }}
    >
      <div className="absolute left-1/2 top-[14%] -translate-x-1/2 whitespace-nowrap">
        <Image
          src="/images/lumina-transparent.png"
          alt="Lumina"
          width={932}
          height={302}
          className="mx-auto block h-auto w-[clamp(9.5rem,18.5vw,17rem)] mix-blend-multiply"
        />
        <div className="mt-[0.2em] font-light tracking-[0.04em] text-[#111827] text-[clamp(0.78rem,1.35vw,1.25rem)]">
          Scientific AI Assistant
        </div>
      </div>

      <h1 className="absolute left-1/2 top-[37%] -translate-x-1/2 m-0 whitespace-nowrap font-serif font-bold leading-none tracking-[0.16em] text-[clamp(1.8rem,4.6vw,4.35rem)] text-transparent bg-clip-text bg-[linear-gradient(180deg,#2b1a08_0%,#050403_40%,#a86b10_61%,#1d1205_100%)] drop-shadow-[0_2px_2px_rgba(0,0,0,0.24)]">
        光照真知<span className="text-[#b8790b]">，</span>无限可能
      </h1>

      <div className="absolute left-1/2 top-[55%] flex w-[38%] -translate-x-1/2 items-center gap-4">
        <div className="h-px flex-1 bg-[linear-gradient(90deg,transparent,rgba(137,89,25,0.45))]" />
        <GlowingDiamond variant="soft" className="size-[clamp(1rem,1.45vw,1.36rem)]" />
        <div className="h-px flex-1 bg-[linear-gradient(90deg,rgba(137,89,25,0.45),transparent)]" />
      </div>

      <div className="absolute left-1/2 top-[60%] -translate-x-1/2 whitespace-nowrap font-serif text-[clamp(0.85rem,2vw,1.85rem)] font-medium tracking-[0.06em] text-[#3a260c] drop-shadow-[0_1px_1px_rgba(255,255,255,0.45)]">
        Illuminating <span className="text-[#b8790b]">Truth, Infinite</span> Possibilities
      </div>

      <div className="absolute left-1/2 top-[73%] flex w-[min(44rem,66vw)] -translate-x-1/2 items-center justify-between text-[#3a260c]">
        <HeroFeature icon={<SunIcon />} cn="启迪探索" en="Inspire Discovery" />
        <HeroSeparator />
        <HeroFeature icon={<AtomIcon />} cn="智能科学" en="Intelligent Science" />
        <HeroSeparator />
        <HeroFeature icon={<NetworkIcon />} cn="连接知识" en="Connect Knowledge" />
        <HeroSeparator />
        <HeroFeature icon={<InfinityIcon />} cn="拓展边界" en="Expand Boundaries" />
      </div>
    </section>
  )
}

function GlowingDiamond({
  className = '',
  variant = 'gold',
}: {
  className?: string
  variant?: 'gold' | 'soft'
}) {
  const isSoft = variant === 'soft'

  return (
    <span
      aria-hidden="true"
      className={`relative inline-flex shrink-0 items-center justify-center ${isSoft ? 'opacity-80' : ''} ${className}`}
    >
      <span
        className={`absolute left-1/2 top-1/2 h-[190%] w-[1.5px] -translate-x-1/2 -translate-y-1/2 rounded-full ${
          isSoft
            ? 'bg-[linear-gradient(180deg,transparent,rgba(255,246,207,0.64)_42%,rgba(255,246,207,0.92)_50%,rgba(255,246,207,0.64)_58%,transparent)]'
            : 'bg-[linear-gradient(180deg,transparent,rgba(255,229,145,0.68)_38%,rgba(255,213,106,0.96)_50%,rgba(255,229,145,0.68)_62%,transparent)]'
        }`}
      />
      <span
        className={`absolute left-1/2 top-1/2 h-[1.5px] w-[94%] -translate-x-1/2 -translate-y-1/2 rounded-full ${
          isSoft
            ? 'bg-[linear-gradient(90deg,transparent,rgba(255,246,207,0.48)_38%,rgba(255,246,207,0.8)_50%,rgba(255,246,207,0.48)_62%,transparent)]'
            : 'bg-[linear-gradient(90deg,transparent,rgba(255,229,145,0.46)_34%,rgba(255,213,106,0.86)_50%,rgba(255,229,145,0.46)_66%,transparent)]'
        }`}
      />
      <span
        className={`absolute inset-[-28%] rounded-full blur-[2px] ${
          isSoft
            ? 'bg-[radial-gradient(circle,rgba(255,246,207,0.34)_0%,rgba(242,217,139,0.2)_42%,transparent_76%)]'
            : 'bg-[radial-gradient(circle,rgba(255,225,136,0.38)_0%,rgba(215,154,16,0.22)_45%,transparent_78%)]'
        }`}
      />
      <span
        className={`relative block h-full w-[68%] [clip-path:polygon(50%_0%,57%_40%,92%_50%,57%_60%,50%_100%,43%_60%,8%_50%,43%_40%)] ${
          isSoft
            ? 'bg-[radial-gradient(circle,#fff6cf_0%,#f2d98b_34%,#e2ae41_62%,rgba(226,174,65,0.2)_82%)] drop-shadow-[0_0_3px_rgba(245,205,100,0.42)]'
            : 'bg-[radial-gradient(circle,#ffe9a6_0%,#f6c552_28%,#c88700_63%,rgba(154,100,0,0.34)_84%)] drop-shadow-[0_0_3px_rgba(255,204,80,0.68)] drop-shadow-[0_0_7px_rgba(210,145,20,0.36)]'
        }`}
      />
    </span>
  )
}

function HeroFeature({ icon, cn, en }: { icon: React.ReactNode; cn: string; en: string }) {
  return (
    <div className="w-[22%] text-center">
      <div className="mx-auto mb-[0.7em] flex h-[clamp(1.8rem,3vw,3.1rem)] items-center justify-center text-[#3a260c]">
        {icon}
      </div>
      <div className="font-serif text-[clamp(0.68rem,1.05vw,1rem)] font-semibold tracking-[0.12em]">
        {cn}
      </div>
      <div className="mt-[0.25em] font-serif text-[clamp(0.55rem,0.82vw,0.8rem)] tracking-[0.02em]">
        {en}
      </div>
    </div>
  )
}

function HeroSeparator() {
  return <div className="h-[clamp(3.2rem,5.6vw,5.5rem)] w-px bg-[rgba(80,50,18,0.55)]" />
}

function SunIcon() {
  return (
    <svg viewBox="0 0 72 72" className="h-full w-full max-w-[3.1rem]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="36" cy="36" r="10" />
      {Array.from({ length: 16 }).map((_, i) => {
        const angle = (i * 22.5 * Math.PI) / 180
        const x1 = 36 + Math.cos(angle) * 20
        const y1 = 36 + Math.sin(angle) * 20
        const x2 = 36 + Math.cos(angle) * 29
        const y2 = 36 + Math.sin(angle) * 29
        return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />
      })}
    </svg>
  )
}

function AtomIcon() {
  return (
    <svg viewBox="0 0 72 72" className="h-full w-full max-w-[3.1rem]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="36" cy="36" r="4" fill="currentColor" stroke="none" />
      <ellipse cx="36" cy="36" rx="26" ry="10" />
      <ellipse cx="36" cy="36" rx="26" ry="10" transform="rotate(60 36 36)" />
      <ellipse cx="36" cy="36" rx="26" ry="10" transform="rotate(120 36 36)" />
    </svg>
  )
}

function NetworkIcon() {
  return (
    <svg viewBox="0 0 72 72" className="h-full w-full max-w-[3.2rem]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M36 8 60 22v28L36 64 12 50V22L36 8Z" />
      <path d="M36 8v20M60 22 43 32M60 50 43 42M36 64V44M12 50l17-8M12 22l17 10" />
      <path d="M29 32 36 28l7 4v10l-7 4-7-4V32Z" />
      {[['36','8'], ['60','22'], ['60','50'], ['36','64'], ['12','50'], ['12','22'], ['36','36']].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r={i === 6 ? 3.5 : 3} fill="currentColor" stroke="none" />
      ))}
    </svg>
  )
}

function InfinityIcon() {
  return (
    <svg viewBox="0 0 72 72" className="h-full w-full max-w-[3.1rem]" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 36c0-8 6-14 14-9 4 2.5 7 6.5 11 9 8 5 14-1 14-9 0-7-5-12-12-12-6 0-11 6-18 21-7 15-12 21-18 21-7 0-12-5-12-12 0-8 6-14 14-9 4 2.5 7 6.5 11 9" transform="translate(8 0) scale(.8 1)" />
    </svg>
  )
}


function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="group p-6 rounded-2xl border border-stone-200/60 bg-white hover:border-stone-300 hover:shadow-sm transition-all">
      <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-4 group-hover:scale-110 transition-transform">
        {icon}
      </div>
      <h3 className="font-semibold text-stone-900 mb-2">{title}</h3>
      <p className="text-sm text-stone-500 leading-relaxed">{description}</p>
    </div>
  )
}

function UseCaseCard({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="p-5 rounded-xl border border-stone-200/40 bg-white hover:border-stone-300 transition-colors">
      <h3 className="font-medium text-stone-900 mb-1.5">{title}</h3>
      <p className="text-sm text-stone-500 leading-relaxed">{description}</p>
    </div>
  )
}
