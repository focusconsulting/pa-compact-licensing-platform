Perform a comprehensive code quality review of the specified file(s) or recent changes using specialized sub-agents.

## Review Process

Launch 5 specialized sub-agents in parallel to analyze the code from different perspectives:

1. **Factual Reviewer** (subagent_type: general-purpose)
   - Verify technical accuracy against official documentation
   - Check API usage matches documentation
   - Validate framework patterns and best practices
   - Confirm dependency versions and compatibility

2. **Senior Engineer** (subagent_type: general-purpose)
   - Review architecture decisions and design patterns
   - Evaluate code structure and organization
   - Assess maintainability and scalability
   - Check for proper separation of concerns
   - Identify potential technical debt

3. **Security Expert** (subagent_type: general-purpose)
   - Identify security vulnerabilities (OWASP Top 10)
   - Check for injection vulnerabilities (SQL, XSS, command injection)
   - Review authentication and authorization logic
   - Assess data validation and sanitization
   - Check for exposed secrets or credentials
   - Review error handling for information leakage

4. **Consistency Reviewer** (subagent_type: general-purpose)
   - Check adherence to project coding standards
   - Verify naming conventions consistency
   - Review code formatting and style
   - Check import organization and structure
   - Validate TypeScript/Python type usage
   - Ensure consistent error handling patterns

5. **Redundancy Checker** (subagent_type: general-purpose)
   - Identify duplicate code and logic
   - Find opportunities for abstraction
   - Locate similar functions that could be consolidated
   - Identify repeated patterns that could be utilities
   - Check for unnecessary code complexity

## Usage

When invoked, you should:

1. Ask the user what to review:
   - Specific file(s) path(s)
   - Recent git changes (staged or committed)
   - Entire module or directory
   - Current IDE selection

2. Launch all 5 agents in parallel using a single message with multiple Task tool calls

3. Wait for all agents to complete

4. Synthesize findings into a comprehensive report with:
   - Executive Summary (critical issues first)
   - Findings by category (Factual, Architecture, Security, Consistency, Redundancy)
   - Prioritized action items (Critical → High → Medium → Low)
   - Code examples and suggested fixes
   - Positive observations (what's done well)

## Report Format

```markdown
# Code Quality Review Report

## Executive Summary
[High-level overview with critical issues highlighted]

## Critical Issues 🚨
[Issues requiring immediate attention]

## Findings by Reviewer

### 📋 Factual Accuracy
- [Findings from factual reviewer]

### 🏗️ Architecture & Design
- [Findings from senior engineer]

### 🔒 Security
- [Findings from security expert]

### 📏 Consistency & Standards
- [Findings from consistency reviewer]

### ♻️ Code Redundancy
- [Findings from redundancy checker]

## Action Items

### Priority 1 (Critical)
- [ ] [Action item with file references]

### Priority 2 (High)
- [ ] [Action item with file references]

### Priority 3 (Medium)
- [ ] [Action item with file references]

### Priority 4 (Low/Enhancement)
- [ ] [Action item with file references]

## Positive Observations ✨
[Things done well that should be maintained]

## Metrics
- Files reviewed: X
- Issues found: X (Critical: X, High: X, Medium: X, Low: X)
- Code redundancy: X instances
- Security concerns: X
```

## Context-Specific Guidelines

### For client/ (Next.js / TypeScript)
- Check Next.js App Router patterns and conventions
- Review React component structure and hooks usage
- Validate TypeScript types and interfaces
- Check client/server component boundaries
- Review styling patterns (PostCSS)
- Validate i18n implementation

### For api/ (Python / FastAPI)
- Check FastAPI route patterns and dependencies
- Review Pydantic model usage and validation
- Validate database access patterns
- Check SQL injection prevention
- Review authentication and authorization logic
- Validate error handling and HTTP status codes

### For iac/ (Infrastructure as Code)
- Check Terraform resource naming conventions
- Review security group and IAM policies
- Validate variable usage and defaults
- Check for hardcoded values that should be variables

## Important Notes

- Run all agents in parallel for efficiency
- Each agent should focus on their specialty
- Agents should read relevant files and context
- Provide specific file paths and line numbers in findings
- Include code snippets showing issues and fixes
- Prioritize findings by impact and effort