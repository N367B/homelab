# Identity and Access

Status: Authentik chosen.

## Decisions

| Decision          | Choice                                          |
| ----------------- | ----------------------------------------------- |
| Identity provider | Authentik                                       |
| Deployment        | Docker Compose on the edge node                 |
| Public domain     | `auth.{{ homelab_domain }}`                     |
| Primary protocol  | OIDC                                            |
| Proxy-side auth   | Authentik forward-auth through Caddy            |
| Admin access      | Private source ranges plus auth where practical |

## Model

Authentik is the central identity provider for services that need SSO.

Use native OIDC when an application supports it well. Use Caddy forward-auth for applications with weak, missing, or inconvenient native auth.

Auth should be chosen per service:

| Auth mode | Use when |
| --- | --- |
| Native | The app has good built-in auth and does not need SSO |
| OIDC | The app supports OIDC cleanly |
| Forward-auth | The app has weak/no auth or should be protected before reaching it |
| Private only | The app is administrative or infrastructure-only |

Admin and infrastructure services default to private. Public exposure must be deliberate.

## Recovery Rule

Do not make Authentik required to recover Authentik.

Keep a break-glass path that works without SSO:

- local console / iLO access
- SSH with keys from trusted admin machines
- direct LAN access to edge services during recovery
- documented restore path for Authentik data and secrets

## Open Items

- Define admin and family users.
- Define groups and naming convention.
- Decide password/passkey/MFA policy.
- Decide which services use native auth, OIDC, forward-auth, or private-only access.
- Decide backup/restore procedure for Authentik database and secrets.
