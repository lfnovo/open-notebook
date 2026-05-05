# Permission Model Design

## Decision

Use scheme A: keep system roles and team roles separate.

- System role remains `app_user.role`, with `admin` and `user`.
- Team authority remains `team_member.role`, with `owner`, `admin`, `member`, and `viewer`.
- A team administrator is a normal system user who is `owner` or `admin` in a specific team.

This avoids a global `team_admin` role because team management rights are scoped to a specific team.

## Permission Levels

### System Administrator

System administrators have `app_user.role = 'admin'`.

They can manage:

- Models and credentials.
- Transformations and default transformation prompts.
- Global settings.
- Advanced system functions.
- Users.
- Teams.

System administrators can create, update, and delete configured models, provider credentials, transformations, global settings, users, and workspace teams.

### Team Administrator

Team administrators have `app_user.role = 'user'` and an active `team_member` row with role `owner` or `admin` for the team they manage.

They can manage only that team:

- Team members.
- The models available to the current team.
- The transformations available to the current team.

Team administrators can only choose from system-defined models and transformations. They cannot create, edit, delete, sync, or configure models, credentials, transformations, or global defaults.

### Regular User

Regular users have `app_user.role = 'user'` and no team management role for the current team.

They can:

- Use resources they own or can access through sharing.
- Use models and transformations allowed by the system and their team context.
- View public content and use normal notebook, source, search, and chat workflows.

They cannot access system management or team management write controls.

## Current Team Scope

For this phase, the current team is the team selected in the team management page or supplied explicitly by team-scoped API endpoints.

Do not introduce a global active-team switcher yet. Team-scoped model and transformation management should be addressed through explicit team routes, such as `/teams/{team_id}/models` and `/teams/{team_id}/transformations`.

## Backend Design

The API remains the source of truth for permissions.

Add or reuse these authorization boundaries:

- `require_admin`: allows only system administrators.
- `ensure_team_manager(team_id, actor)`: allows system administrators and active team `owner` or `admin` members for the given team.
- Standard authenticated access: allows active logged-in users for normal product use.

System-admin-only writes must include:

- Model creation, deletion, provider discovery and sync, default model assignment, model testing where it depends on credentials.
- Credential creation, update, deletion, migration, discovery, model registration, and connection testing.
- Transformation creation, update, deletion, and default prompt updates.
- Global settings updates.
- User management.
- Team creation and deletion.
- Audit log access and other advanced administration.

Team-manager writes must include:

- Adding, updating, and removing members for a specific non-system team.
- Updating the model allowlist for a specific team.
- Updating the transformation allowlist for a specific team.

Team managers may view the available system models and transformations for selection, but the response must not expose provider secrets or editable credential fields.

## Data Model

Add team-scoped allowlist tables or equivalent named repository records:

- `team_model`
  - `team`: `record<team>`
  - `model`: `record<model>`
  - `created_by`: optional `record<app_user>`
  - `created`: datetime
  - Unique index on `team, model`

- `team_transformation`
  - `team`: `record<team>`
  - `transformation`: `record<transformation>`
  - `created_by`: optional `record<app_user>`
  - `created`: datetime
  - Unique index on `team, transformation`

System team `team:public` remains read-only and cannot have members, model allowlists, or transformation allowlists managed through the workspace team UI.

## Frontend Design

The sidebar should reflect the same permission model as the API:

- Regular users see only product usage routes and profile.
- Team administrators see a team management entry for teams they manage.
- System administrators see the full system management group.

The existing team settings page can remain the first team-management surface, but controls should adapt to authority:

- System administrators can create, rename, delete teams, and manage members.
- Team administrators can manage members for teams where they are `owner` or `admin`.
- Team administrators can select allowed models and transformations for those teams.
- Team administrators must not see API key, credential, model creation, model deletion, transformation authoring, global settings, or advanced system controls unless they are also system administrators.

System model and transformation configuration pages remain system-admin-only. Team allowlist selection should be presented as a separate team-scoped section, not by reusing editable system configuration forms.

## Error Handling

Permission failures return `403` with role-specific messages:

- `Admin privileges required` for system-only actions.
- `Team owner or admin privileges required` for team-scoped management actions.

Missing teams, users, models, or transformations return `404`. Attempts to manage system teams return `400`.

When a team allowlist references a deleted model or transformation, list endpoints should omit unavailable entries and save endpoints should reject unknown IDs.

## Testing

Backend tests should cover:

- System administrators can access system management writes.
- Regular users cannot access system management writes.
- Team owners and team admins can manage members and team allowlists for their own team.
- Team members and viewers cannot manage members or team allowlists.
- Team managers cannot create, update, delete, sync, or configure models, credentials, transformations, settings, users, or advanced audit data.
- System team `team:public` remains protected from team member and allowlist management.

Frontend tests should cover:

- Sidebar visibility for system administrators, team administrators, and regular users.
- Team management page controls for system administrators versus team administrators.
- Team-scoped model and transformation multi-select surfaces do not expose system configuration actions.

## Implementation Notes

Implementation should proceed in thin, testable slices:

1. Add backend authorization helpers and tests for existing team manager behavior.
2. Protect system configuration routes with `require_admin`.
3. Add team model and transformation allowlist repositories, migrations, routes, and tests.
4. Update frontend permission state and sidebar visibility.
5. Add team-scoped model and transformation selection UI.
6. Run backend and frontend regression tests, plus manual checks with admin, team admin, and regular user accounts.
