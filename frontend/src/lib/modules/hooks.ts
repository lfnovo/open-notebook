'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { moduleRepository } from './repository'
import type { ModuleUpdate } from './types'

export const moduleKey = ['module-catalog'] as const
export function useModules() {
  return useQuery({ queryKey: moduleKey, queryFn: () => moduleRepository.list(), retry: false, staleTime: 10_000, refetchInterval: 30_000 })
}
export function useModuleUpdate() {
  const client = useQueryClient()
  return useMutation({ mutationFn: (change: ModuleUpdate) => moduleRepository.update(change),
    retry: false, onSuccess: data => { client.setQueryData(moduleKey, data) },
  })
}
