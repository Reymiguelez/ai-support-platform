# Contributing

Thank you for taking the time to improve AI Support Platform.

## Development workflow

Create a focused branch from `main`, make the smallest coherent change, and add tests for behavior that changes. Keep business rules in application or domain services rather than embedding them in API handlers or prompt strings.

Before opening a pull request, run the relevant backend and frontend checks:

```bash
make test
make lint
make format
```

If a change introduces a new environment variable, migration, integration, or operational requirement, update `.env.example` and the relevant documentation in the same pull request.

## Pull requests

Pull requests should explain the problem, the implementation approach, how the change was tested, and any follow-up work. Screenshots or API examples are helpful for user-facing changes. Do not include credentials, customer data, private documents, or generated dependency directories in commits.

## Commit style

Use short, imperative commit subjects. Conventional Commit prefixes such as `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, and `chore:` are encouraged because they make the project history easier to scan.
