import type { ComponentType, SVGProps } from 'react'

/** Sidebar or app navigation entry. */
export interface NavItem {
  name: string
  href: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

/** Shared Next.js App Router page props shape. */
export interface PageProps {
  params: { [key: string]: string }
  searchParams: { [key: string]: string | string[] | undefined }
}
