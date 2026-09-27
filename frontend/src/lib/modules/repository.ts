import { apiClient } from '@/lib/api/client'
import type { ModuleInfo, ModuleUpdate } from './types'

/** Public data port. Views and domain models never depend on Axios. */
export interface ModuleRepository {
  list(): Promise<ModuleInfo[]>
  update(change: ModuleUpdate): Promise<ModuleInfo[]>
  exportConfiguration(): Promise<unknown>
}
export class HttpModuleRepository implements ModuleRepository {
  async list() { return (await apiClient.get<ModuleInfo[]>('/modules')).data }
  async update({ id, ...change }: ModuleUpdate) {
    return (await apiClient.put<ModuleInfo[]>('/modules/' + encodeURIComponent(id), change)).data
  }
  async exportConfiguration() { return (await apiClient.get('/modules/configuration')).data }
}
export const moduleRepository: ModuleRepository = new HttpModuleRepository()
