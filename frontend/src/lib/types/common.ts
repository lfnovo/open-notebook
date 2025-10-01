import type { ComponentType, SVGProps } from 'react'

export interface NavItem {
  name: string
  href: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

export interface PageProps {
  params: { [key: string]: string }
  searchParams: { [key: string]: string | string[] | undefined }
}
