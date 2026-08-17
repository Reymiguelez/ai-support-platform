# Security Policy

## Scope

This project is a portfolio-grade reference implementation of an AI customer support platform. It is not a substitute for a production security review, threat model, or compliance assessment.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Contact the repository owner privately with a clear description of the affected component, reproduction steps, impact assessment, and any suggested mitigation. Allow reasonable time for investigation and remediation before publicly disclosing the issue.

## Secret handling

Never commit `.env` files, API keys, private keys, certificates, production database credentials, customer records, or private support documents. Use `.env.example` as the shareable configuration contract and inject real values through a local environment, CI secret store, or deployment secret manager.

If a credential is accidentally committed, revoke or rotate it immediately. Removing the file in a later commit is not sufficient because the value may remain in Git history.

## Production hardening checklist

Before deploying this application to a real environment, configure TLS, managed secrets, least-privilege database access, tenant isolation, audit-log retention, dependency scanning, backups, rate limits, structured monitoring, and a documented incident-response process. Review every external AI and business-action integration for authorization, data minimization, and failure handling.
