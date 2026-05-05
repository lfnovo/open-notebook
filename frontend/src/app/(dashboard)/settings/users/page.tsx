'use client'

import { FormEvent, useEffect, useState } from 'react'
import { Edit, KeyRound, Loader2, Plus, Search, UserCog } from 'lucide-react'
import { UserListItem, UserRole, UserStatus } from '@/lib/api/users'
import {
  useCreateUser,
  useResetUserPassword,
  useUpdateUser,
  useUsers,
} from '@/lib/hooks/use-users'
import { useTranslation } from '@/lib/hooks/use-translation'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { OperationGuide } from '@/components/common/OperationGuide'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const USER_ROLES: UserRole[] = ['user', 'admin']
const USER_STATUSES: UserStatus[] = ['active', 'disabled']

function roleLabel(role: UserRole, t: ReturnType<typeof useTranslation>['t']) {
  return role === 'admin' ? t.users.roleAdmin : t.users.roleUser
}

function statusLabel(status: UserStatus, t: ReturnType<typeof useTranslation>['t']) {
  return status === 'active' ? t.users.statusActive : t.users.statusDisabled
}

function UserDialog({
  open,
  user,
  onOpenChange,
  onTemporaryPassword,
}: {
  open: boolean
  user?: UserListItem | null
  onOpenChange: (open: boolean) => void
  onTemporaryPassword: (password: string) => void
}) {
  const { t } = useTranslation()
  const createUser = useCreateUser()
  const updateUser = useUpdateUser()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('user')
  const [status, setStatus] = useState<UserStatus>('active')

  useEffect(() => {
    setUsername(user?.username || '')
    setEmail(user?.email || '')
    setDisplayName(user?.display_name || '')
    setPassword('')
    setRole(user?.role || 'user')
    setStatus(user?.status || 'active')
  }, [open, user])

  const isEditing = !!user
  const isPending = createUser.isPending || updateUser.isPending

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (isPending) return

    if (user) {
      updateUser.mutate(
        {
          userId: user.id,
          data: {
            display_name: displayName.trim() || undefined,
            role,
            status,
          },
        },
        { onSuccess: () => onOpenChange(false) }
      )
    } else {
      createUser.mutate(
        {
          username: username.trim(),
          email: email.trim() || undefined,
          display_name: displayName.trim() || undefined,
          role,
          password: password.trim() || undefined,
        },
        {
          onSuccess: (result) => {
            if (result.temporary_password) {
              onTemporaryPassword(result.temporary_password)
            }
            onOpenChange(false)
          },
        }
      )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          <DialogHeader>
            <DialogTitle>{isEditing ? t.users.editUser : t.users.createUser}</DialogTitle>
          </DialogHeader>
          {!isEditing && (
            <>
              <div className="space-y-2">
                <Label htmlFor="username">{t.users.username}</Label>
                <Input
                  id="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">{t.users.email}</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
            </>
          )}
          <div className="space-y-2">
            <Label htmlFor="display-name">{t.users.displayName}</Label>
            <Input
              id="display-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </div>
          {!isEditing && (
            <div className="space-y-2">
              <Label htmlFor="password">{t.users.password}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={t.users.passwordPlaceholder}
              />
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>{t.users.role}</Label>
              <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {USER_ROLES.map((item) => (
                    <SelectItem key={item} value={item}>
                      {roleLabel(item, t)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {isEditing && (
              <div className="space-y-2">
                <Label>{t.users.status}</Label>
                <Select value={status} onValueChange={(value) => setStatus(value as UserStatus)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {USER_STATUSES.map((item) => (
                      <SelectItem key={item} value={item}>
                        {statusLabel(item, t)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t.common.cancel}
            </Button>
            <Button type="submit" disabled={(!isEditing && !username.trim()) || isPending}>
              {isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t.common.save}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function UsersPage() {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [role, setRole] = useState<UserRole | 'all'>('all')
  const [status, setStatus] = useState<UserStatus | 'all'>('all')
  const [createOpen, setCreateOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null)
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null)
  const { data, isLoading, error } = useUsers({ q: query, role, status })
  const resetPassword = useResetUserPassword()
  const users = data?.items ?? []

  const handleResetPassword = (userId: string) => {
    resetPassword.mutate(userId, {
      onSuccess: (result) => setTemporaryPassword(result.temporary_password),
    })
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <LoadingSpinner />
      </div>
    )
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <UserCog className="h-6 w-6 text-muted-foreground" />
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">{t.navigation.users}</h1>
            <p className="text-sm text-muted-foreground">{t.users.description}</p>
          </div>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          {t.users.createUser}
        </Button>
      </div>

      <div className="flex flex-col gap-3 lg:flex-row">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="pl-9"
            placeholder={t.users.searchUsers}
          />
        </div>
        <Select value={role} onValueChange={(value) => setRole(value as UserRole | 'all')}>
          <SelectTrigger className="w-full lg:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.users.allRoles}</SelectItem>
            {USER_ROLES.map((item) => (
              <SelectItem key={item} value={item}>
                {roleLabel(item, t)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={(value) => setStatus(value as UserStatus | 'all')}>
          <SelectTrigger className="w-full lg:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t.users.allStatuses}</SelectItem>
            {USER_STATUSES.map((item) => (
              <SelectItem key={item} value={item}>
                {statusLabel(item, t)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <OperationGuide
        title={t.users.guideTitle}
        description={t.users.guideDescription}
        steps={[
          t.users.guideReviewIdentity,
          t.users.guideApplyLeastPrivilege,
          t.users.guideVerifyAudit,
        ]}
      />

      {error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {t.common.error}
        </div>
      ) : users.length === 0 ? (
        <div className="rounded-md border p-8 text-center text-sm text-muted-foreground">
          {t.users.empty}
        </div>
      ) : (
        <div className="overflow-hidden rounded-md border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">{t.users.user}</th>
                <th className="px-4 py-3 font-medium">{t.users.role}</th>
                <th className="px-4 py-3 font-medium">{t.users.status}</th>
                <th className="px-4 py-3 font-medium">{t.users.resources}</th>
                <th className="px-4 py-3 font-medium">{t.users.lastLogin}</th>
                <th className="w-28 px-4 py-3 text-right font-medium">{t.common.actions}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-t">
                  <td className="px-4 py-3">
                    <div className="font-medium">{user.display_name || user.username}</div>
                    <div className="text-xs text-muted-foreground">{user.email || user.username}</div>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={user.role === 'admin' ? 'secondary' : 'outline'}>
                      {roleLabel(user.role, t)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={user.status === 'active' ? 'outline' : 'secondary'}>
                      {statusLabel(user.status, t)}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {t.common.source}: {user.source_count} · {t.common.notebook}: {user.notebook_count}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {user.last_login_at || t.common.unknown}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingUser(user)}
                        aria-label={t.users.editUser}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        disabled={resetPassword.isPending}
                        onClick={() => handleResetPassword(user.id)}
                        aria-label={t.users.resetPassword}
                      >
                        <KeyRound className="h-4 w-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <UserDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onTemporaryPassword={setTemporaryPassword}
      />
      <UserDialog
        open={!!editingUser}
        user={editingUser}
        onOpenChange={(open) => !open && setEditingUser(null)}
        onTemporaryPassword={setTemporaryPassword}
      />
      <Dialog open={!!temporaryPassword} onOpenChange={(open) => !open && setTemporaryPassword(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t.users.temporaryPassword}</DialogTitle>
          </DialogHeader>
          <div className="rounded-md border bg-muted/40 p-3 font-mono text-sm">
            {temporaryPassword}
          </div>
          <DialogFooter>
            <Button onClick={() => setTemporaryPassword(null)}>{t.common.done}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
