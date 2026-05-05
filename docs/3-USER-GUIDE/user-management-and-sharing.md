# User Management, Teams, and Sharing

This guide describes the standard operating flow for user access, team membership, and resource sharing.

Use it whenever you create users, change roles, add team members, share a source or notebook, or revoke public access.

---

## Operating Principles

1. **Confirm the identity first.** Check the user, team, and resource before changing access.
2. **Use the smallest useful permission.** Prefer normal user roles, team membership, and read-only sharing unless admin access is required.
3. **Review the result.** After each change, check the user/team state, current share grants, and audit log.

---

## Manage Users

Administrators can open **Settings -> Users** to manage accounts.

Standard flow:

1. Search for the existing account before creating a new one.
2. Create the user with a clear username, email, display name, and initial role.
3. Leave the password blank when you want Lumina to generate a temporary password.
4. Assign `User` by default. Use `Admin` only for people who manage system settings, users, teams, credentials, or audit review.
5. Disable users instead of deleting them when they still own sources or notebooks.
6. After role, status, or password changes, review the audit log.

Notes:

- Disabled users cannot sign in.
- Public content owned by a disabled user remains public until an owner or admin revokes sharing.
- Password reset produces a temporary password. Share it through a trusted channel outside Lumina.

---

## Manage Teams

Administrators and team managers can open **Settings -> Teams** to create teams and manage members.

Standard flow:

1. Create a team for a stable working group, not for a one-off share.
2. Add only active users.
3. Use the smallest team role that fits the member's job.
4. Review existing shares before removing members or deleting teams.
5. Remove or disable members who no longer need access.
6. Check the audit log after membership changes.

Team roles:

| Role | Use for |
| --- | --- |
| Owner | People accountable for the team and membership. |
| Admin | People who help manage members. |
| Member | Normal collaborators who need shared resources. |
| Viewer | Read-only participants. |

The `Public` team is a system group. You cannot add members to it. Sharing with `Public` means sharing to the web.

---

## Share Resources

Resource owners and system administrators can share sources and notebooks.

Standard flow:

1. Open the share dialog from the source or notebook.
2. Choose one target: a specific team or **Public**.
3. Confirm that this phase grants read-only access.
4. For public sharing, read the warning carefully before confirming.
5. After saving, review **Current access** in the share dialog.
6. Use **Advanced -> Audit Log** to confirm who changed access and when.

Public sharing means:

- Anyone who can reach the public browse page or public link can read the resource.
- Other users or teams can reference the public resource as read-only material in their notebooks.
- Public sharing can be revoked, but existing read-only references are preserved so existing notebooks do not break.
- Public revocation removes anonymous/public discovery access; it does not recall content that was already downloaded, copied, or exported.

Team sharing means:

- Active team members can read the shared resource.
- Removing a team grant removes future team access to that resource.
- Removing a user from a team removes access that came through that team, unless the user has another direct or team grant.

---

## Review Audit Events

Open **Advanced -> Audit Log** after important account or sharing changes.

Look for:

- `user.created`, `user.updated`, `user.password_reset`
- `team.created`, `team.updated`, `team.deleted`
- `team.member_upserted`, `team.member_removed`
- `share.public_enabled`, `share.public_revoked`, `share.grant_created`, `share.grant_deleted`

Use actor, target, and metadata filters to confirm that the intended change happened and to spot unexpected changes.

---

## Quick Checklist

Before changing access:

- Confirm the user or team.
- Confirm the source or notebook.
- Confirm whether the change should be private, team-only, or public.

After changing access:

- Review the visible state in the page.
- Review current share grants.
- Review audit events for sensitive changes.
