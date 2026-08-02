# Security policy

## Secrets

OAuth client IDs and secrets are never committed to this repository. Runtime
credentials are supplied through environment variables on the private worker.

The application does not log OAuth tokens, client secrets, raw API responses, or
the bodies of Reddit posts and comments.

## Network access

The Reddit module connects only to Reddit's documented OAuth and API hosts:

- `https://www.reddit.com/api/v1/access_token`
- `https://oauth.reddit.com/`

Submitted URLs are validated against an allowlist of Reddit hostnames before an
identifier is extracted. The client does not follow user-supplied URLs to
arbitrary hosts.

## Reporting

Security or privacy concerns may be reported through the repository's GitHub
issue tracker without including secrets or personal data.

