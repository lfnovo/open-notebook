import { ModulePage } from '@/components/modules/ModulePage'
export default async function Page({ params }: { params: Promise<{ moduleId: string }> }) {
  const { moduleId } = await params
  return <ModulePage id={moduleId} />
}
