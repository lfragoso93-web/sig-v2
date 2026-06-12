import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'

// ── Types ──────────────────────────────────────────

export interface UpdateProfilePayload {
  name?: string
  email?: string
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
}

// ── Hook principal ─────────────────────────────────

export function useUpdateProfile() {
  const { refreshUser, setUser } = useAuth()

  return useMutation({
    mutationFn: (payload: UpdateProfilePayload) =>
      api.patch('/users/me', payload).then(r => r.data),
    onSuccess: (data) => {
      // Atualiza otimisticamente sem re-fetch
      setUser(prev => prev ? { ...prev, ...data } : prev)
    },
    onSettled: () => refreshUser(),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) =>
      api.patch('/users/me/password', payload).then(r => r.data),
  })
}

export function useUpdateAvatar() {
  const { refreshUser, setUser } = useAuth()

  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api.patch('/users/me/avatar', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data)
    },
    onSuccess: (data) => {
      setUser(prev => prev ? { ...prev, avatar_url: data.avatar_url } : prev)
    },
    onSettled: () => refreshUser(),
  })
}

export function useDeleteAccount() {
  const { logout } = useAuth()
  const qc = useQueryClient()

  return useMutation({
    mutationFn: () => api.delete('/users/me').then(r => r.data),
    onSuccess: () => {
      qc.clear()
      logout()
    },
  })
}
