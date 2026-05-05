import { GuestHeader } from '@/components/common/GuestHeader'

interface AuthPageShellProps {
  title: string
  description: string
  children: React.ReactNode
}

export function AuthPageShell({ title, description, children }: AuthPageShellProps) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-stone-50 to-white">
      <GuestHeader primaryHref="/public" primaryLabel="公开内容" />

      <main className="px-6 py-10 sm:py-14">
        <section className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[minmax(0,0.95fr)_minmax(360px,520px)] lg:items-center">
          <div className="max-w-xl text-stone-700">
            <div className="mb-4 inline-flex rounded-full border border-stone-200 bg-white/70 px-3 py-1 text-sm text-stone-500">
              Lumina Account
            </div>
            <h1 className="text-3xl font-bold tracking-normal text-stone-900 sm:text-4xl">
              {title}
            </h1>
            <p className="mt-4 text-base leading-relaxed text-stone-500 sm:text-lg">
              {description}
            </p>
          </div>

          <div className="flex justify-center lg:justify-end">
            {children}
          </div>
        </section>
      </main>
    </div>
  )
}
