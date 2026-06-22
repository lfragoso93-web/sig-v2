import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { classTargetsService } from '@/services/classTargetsService'

export function useClassTargets(portfolioId: number | null) {
  return useQuery({
    queryKey: ['class-targets', portfolioId],
    queryFn: () => classTargetsService.list(portfolioId!),
    enabled: !!portfolioId,
  })
}

export function useUpsertClassTarget(portfolioId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ asset_type, target_pct }: { asset_type: string; target_pct: number }) =>
      classTargetsService.upsert(portfolioId!, asset_type, target_pct),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['class-targets', portfolioId] }),
  })
}

export function useDeleteClassTarget(portfolioId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (asset_type: string) => classTargetsService.remove(portfolioId!, asset_type),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['class-targets', portfolioId] }),
  })
}
