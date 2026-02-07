# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of DocuMind seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Security vulnerabilities should not be reported through public GitHub issues.

### 2. Contact Us Privately

Send details to: [mohammed.saber.business@gmail.com](mailto:mohammed.saber.business@gmail.com)

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution Target**: Within 30 days (depending on severity)

### 4. Disclosure Policy

- We will acknowledge your contribution in release notes (unless you prefer anonymity)
- We follow responsible disclosure practices
- Please allow us reasonable time to address the issue before public disclosure

## Security Best Practices

When deploying DocuMind:

1. **Environment Variables**: Never commit `.env` files with real credentials
2. **API Keys**: Use environment variables for all API keys
3. **Database**: Enable authentication for MongoDB
4. **Network**: Use firewalls to restrict database access
5. **Updates**: Keep dependencies updated for security patches

## Known Security Considerations

- **File Uploads**: Validate file types and sizes
- **API Rate Limiting**: Consider implementing rate limits for production
- **Authentication**: Implement authentication for production deployments

Thank you for helping keep DocuMind secure!
