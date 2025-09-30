export interface NavItem {
  name: string
  href: string
  icon: any
}

export interface PageProps {
  params: { [key: string]: string }
  searchParams: { [key: string]: string | string[] | undefined }
}