# Security Policy

## Supported Versions

We release security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Privacy & Data Handling

Local Web Memory is designed with **privacy-first** principles:

### What We Store Locally
- ✅ Web page URLs, titles, and extracted content
- ✅ AI-generated keywords and descriptions  
- ✅ Vector embeddings for semantic search
- ✅ User preferences and settings

### What We DON'T Store
- ❌ Personal identifiable information (PII)
- ❌ Authentication credentials or cookies
- ❌ Sensitive form data or payment information
- ❌ Private browsing history
- ❌ Data from excluded domains

### Data Location
- **100% Local Storage**: All data stored on your machine only
- **No Cloud Sync**: No data transmitted to external servers
- **User Control**: Complete control over data with export/delete options

## External API Usage

### ByteDance Ark API
- **Purpose**: Generate keywords/descriptions and vector embeddings
- **Data Sent**: Only webpage content (title + extracted text)
- **Data NOT Sent**: URLs, user identity, browsing patterns
- **Fallback**: Works with mock data if API unavailable

### API Security
- API keys stored securely in environment variables
- No hardcoded credentials in source code
- Timeout and retry mechanisms prevent API abuse
- Error handling prevents data leakage in logs

## Chrome Extension Security

### Permissions
- **Minimal Permissions**: Only essential permissions requested
- **tabs**: Access tab information for content extraction
- **activeTab**: Access current tab content only
- **storage**: Local storage for user preferences
- **scripting**: Content script injection

### Content Security
- **Manifest V3**: Latest Chrome extension security model
- **Content Script Isolation**: Isolated execution context
- **No Eval**: No dynamic code execution
- **CSP Headers**: Content Security Policy enforcement

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### Reporting Process

1. **DO NOT** create a public GitHub issue for security vulnerabilities
2. **Email** security concerns to: [security@localwebmemory.dev] (replace with actual email)
3. **Include** detailed information:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if you have one)

### Response Timeline

- **Initial Response**: Within 48 hours
- **Assessment**: Within 1 week  
- **Fix Development**: Within 2-4 weeks (depending on severity)
- **Public Disclosure**: After fix is deployed

### Responsible Disclosure

- We will acknowledge your contribution in release notes (with your permission)
- We may offer a small bounty for significant security findings
- We will coordinate disclosure timeline with you

## Security Best Practices

### For Users

- **Keep Updated**: Always use the latest version
- **Review Permissions**: Understand what permissions you're granting
- **Secure Environment**: Keep your OS and browser updated
- **Backup Data**: Export your data regularly
- **Check Exclusions**: Review domain exclusion settings

### For Developers

- **Code Reviews**: All security-related code must be peer reviewed
- **Dependency Updates**: Regular security updates for dependencies
- **Input Validation**: All user inputs are validated and sanitized
- **Error Handling**: No sensitive data in error messages or logs
- **Secure Storage**: Sensitive data encrypted where possible

## Known Security Considerations

### Local Storage Risks
- Data stored unencrypted on local filesystem
- Other applications with filesystem access could potentially read data
- **Mitigation**: Store in user-specific directories with appropriate permissions

### API Communication
- HTTPS enforced for all external API communication
- API keys transmitted securely
- **Mitigation**: No sensitive user data sent to APIs

### Extension Risks
- Content scripts run in webpage context
- Potential for malicious website interference
- **Mitigation**: Isolated execution and minimal DOM interaction

## Compliance

- **GDPR**: User data control, deletion rights, no unnecessary collection
- **CCPA**: User privacy rights, data transparency
- **Chrome Web Store**: Compliance with extension store policies

For questions about this security policy, please contact: [security@localwebmemory.dev]