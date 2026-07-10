# GitHub Copilot Custom Agents - Complete Team Configuration

This directory contains a configured team of specialized AI agents that collaborate to deliver high-quality features through a structured, repeatable workflow.

## 🧩 Agent Team Overview

| Agent | Role | Input | Output | Handoff To |
|-------|------|-------|--------|-----------|
| **Product Owner** | Transform user intent into testable requirements | User request, feature ideas | User Stories with acceptance criteria | Architect |
| **Architect** | Translate requirements into technical plans | User Stories, acceptance criteria | Implementation plan with phases and files | Developer |
| **Developer** | Implement features following the plan | Implementation plan, architecture | Code changes, tests, commits | Tester |
| **Tester** | Validate correctness and quality | Implementation, tests, requirements | Pass/Fail decision with evidence | Product Owner / Developer |

## � File Structure

This directory contains two types of documents:

### Agent Configuration Files (`.agent.md`)
These are **operational files** discovered and used by VS Code:
- `product-owner.agent.md` - Product Owner Agent (YAML config + detailed documentation)
- `architect.agent.md` - Architect Agent (YAML config + detailed documentation)
- `developer.agent.md` - Developer Agent (YAML config + detailed documentation)
- `tester.agent.md` - Tester & Validator Agent (YAML config + detailed documentation)

Each file contains:
- **YAML frontmatter** with tool configurations (used by VS Code)
- **Markdown body** with purpose, responsibilities, input/output formats, constraints, and decision rules

### Reference Documentation
- `AGENTS_WORKFLOW.md` (this file) - Strategic overview, workflow diagrams, quality gates, and cross-agent context

## �🔄 Workflow

### Primary Flow: Successful Feature

```
1. User Request
        ↓
2. Product Owner Agent
   ├─ Analyze intent
   ├─ Define user stories
   ├─ Add acceptance criteria
   └─ → Handoff to Architect
        ↓
3. Architect Agent
   ├─ Analyze requirements
   ├─ Design system architecture
   ├─ Create implementation plan
   └─ → Handoff to Developer
        ↓
4. Developer Agent
   ├─ Implement features
   ├─ Write tests
   ├─ Follow code standards
   └─ → Handoff to Tester
        ↓
5. Tester Agent
   ├─ Validate all criteria met
   ├─ Run tests (97%+ coverage)
   ├─ Check for regressions
   └─ → ✅ APPROVED
        ↓
6. Product Owner (Final Confirmation)
   └─ Sign-off on completion
```

### Iteration Flow: Issues Found

```
5. Tester Agent (FAILED)
   ├─ Identify issues
   ├─ Document root causes
   └─ → Handoff back to Developer
        ↓
4b. Developer Agent (Fixes)
   ├─ Address issues
   ├─ Rerun tests
   └─ → Handoff to Tester
        ↓
5b. Tester Agent (Revalidate)
   └─ → ✅ APPROVED or 🔄 More Fixes
```

### Decision Points

```
Architect Issues → Tester escalates to Architect for review
Architecture errors OR missing design details → Architect revises plan

Requirements Unclear → Tester escalates to Product Owner for clarification
Acceptance criteria ambiguous → Product Owner clarifies and confirms
```

## 📋 Standardized Output Formats

### Product Owner Output

```markdown
## User Story Analysis

### Feature Summary
[Concise description]

### Stakeholders & Concerns
- [Stakeholder]: [Concerns]

### User Stories
#### Story 1: [Title]
- As a [stakeholder]
- I want [capability]
- So that [benefit]
- Acceptance Criteria: [Testable criteria]

### Assumptions
[List assumptions]

### Related Documentation
- README.md: [References]
- ARCHITECTURE.md: [References]
```

### Architect Output

```markdown
## Feature Summary
[Concise description]

## Architecture Analysis
- Components affected: [List]
- Design decisions: [List with rationale]

## Implementation Plan
### Phase 1: [Phase Name]
- Step 1: [File], [Action], [Details]
- Step 2: [File], [Action], [Details]

## Files to Modify
- To Create: [Files and purposes]
- To Modify: [Files and changes]

## Test Strategy
- Unit tests: [What to test]
- Integration tests: [What to test]

## Risks & Mitigations
[Risk assessment table]
```

### Developer Output

```markdown
## Changes Made
[Summary of implementation]

## Files Modified
- Created: [Files]
- Modified: [Files and changes]

## Tests Added/Updated
- New unit tests: [Count and purpose]
- Coverage: Before [X]% → After [Y]%

## Code Quality
- ✅ Linting: Passed
- ✅ Type hints: All present
- ✅ Docstrings: All present
- ✅ Git commits: All reference PRO ticket
```

### Tester Output

```markdown
## Validation Result
**Status:** ✅ PASSED / ❌ FAILED

## Acceptance Criteria Validation
- Criterion 1: ✅ PASSED
- Criterion 2: ✅ PASSED
- Criterion N: ❌ FAILED (Issue: ...)

## Test Results
- Tests: [N passed, M failed]
- Coverage: [X]% (Target: 97%)
- Regressions: None / [List]

## Issues Found
[If any, list with severity and fix recommendations]

## Decision
✅ Ready for Production / ❌ Return to Developer for fixes
```

## 🎯 Agent Tools

Each agent is configured with specific tools in its respective `.agent.md` file:

- **[product-owner.agent.md](product-owner.agent.md)** → `codebase`, `search`, `fetch`, `readFile`, `listFiles`
- **[architect.agent.md](architect.agent.md)** → `codebase`, `search`, `readFile`, `listFiles`
- **[developer.agent.md](developer.agent.md)** → `editFiles`, `terminal`, `runTests`, `readFile`, `codebase`
- **[tester.agent.md](tester.agent.md)** → `runTests`, `terminal`, `codebase`, `diff`, `readFile`

See individual agent files for detailed descriptions of tool usage.

## 🚀 Using This Agent Team

### Step 1: Start with Product Owner

**Command:**
```
@product-owner

Analyze this feature request:
[Your feature request]
```

**Output:** User Stories with acceptance criteria

### Step 2: Send to Architect

**Command:**
```
@architect

Design the implementation for these requirements:

[Product Owner output]
```

**Output:** Implementation plan with phases and files

### Step 3: Send to Developer

**Command:**
```
@developer

Implement the following architecture plan:

[Architect output]

Constraints:
- Follow doc/CONTRIBUTING.md
- Add tests per doc/TESTING.md
```

**Output:** Code changes, tests, commits

### Step 4: Send to Tester

**Command:**
```
@tester

Validate this implementation against acceptance criteria:

Acceptance Criteria:
[From Product Owner output]

Implementation:
[From Developer output]
```

**Output:** Pass/Fail decision with evidence

## 📚 Documentation Foundation

All agents operate on shared context from:

1. **README.md** - Project overview, quick start, structure
   - Used by all agents for domain understanding
   - Referenced for project goals and constraints

2. **doc/ARCHITECTURE.md** - System design and patterns
   - Used by Architect for design decisions
   - Used by Developer for implementation patterns
   - Used by Tester for integration validation

3. **doc/CONTRIBUTING.md** - Coding standards and workflows
   - Used by Developer for code style
   - Used by Tester for quality assessment
   - Used by all agents for commit conventions

4. **doc/TESTING.md** - Testing strategy and requirements
   - Used by Architect for test planning
   - Used by Developer for test implementation
   - Used by Tester for coverage validation

## ✅ Quality Gates

### Product Owner Gate
✓ Requirements are testable and unambiguous
✓ All acceptance criteria are concrete
✓ No technical implementation details

### Architect Gate
✓ Architecture aligns with ARCHITECTURE.md
✓ Design is minimal and justified
✓ Implementation plan is complete

### Developer Gate
✓ Code follows CONTRIBUTING.md
✓ Tests cover new/modified code (97%+ coverage)
✓ No regressions in existing tests
✓ All commits reference PRO ticket

### Tester Gate
✓ All acceptance criteria verified
✓ Test suite passes with 97%+ coverage
✓ No regressions detected
✓ Code quality meets standards

## 🔍 Monitoring & Handoff Rules

### Handoff Checklist

**Product Owner → Architect:**
- [ ] User Stories clearly written
- [ ] Acceptance criteria are testable
- [ ] Assumptions documented
- [ ] Documentation references included

**Architect → Developer:**
- [ ] Implementation phases defined
- [ ] Specific files listed
- [ ] Test strategy clear
- [ ] Dependencies documented

**Developer → Tester:**
- [ ] All code changes made
- [ ] Tests written and passing
- [ ] Coverage maintained/improved
- [ ] Commits reference PRO ticket

**Tester → Product Owner (if passed):**
- [ ] All criteria verified
- [ ] Test results attached
- [ ] No critical issues
- [ ] Ready for production

**Tester → Developer (if failed):**
- [ ] Issues documented with severity
- [ ] Evidence provided (test output, logs)
- [ ] Root causes identified
- [ ] Clear path to fixes

## 🛡️ Constraints & Boundaries

| Agent | Can Do | Cannot Do |
|-------|--------|-----------|
| **Product Owner** | ✅ Define requirements | ❌ Propose technical solutions |
| **Architect** | ✅ Design architecture | ❌ Change requirements |
| **Developer** | ✅ Implement code | ❌ Modify architecture |
| **Tester** | ✅ Validate & approve | ❌ Approve without verification |

## 🎓 Best Practices

1. **Clarity First**: Ensure each handoff is complete and unambiguous
2. **Documentation**: Always reference project documentation
3. **Data-Driven**: Base all decisions on evidence (test results, metrics)
4. **Iteration**: If issues found, loop back to relevant agent
5. **Audit Trail**: Keep all outputs for traceability

## 📊 Workflow Examples

### Example 1: Complete Happy Path

```
PO: "Add time entry validation"
  ↓ (User Stories + Criteria)
Architect: Design validation module
  ↓ (Implementation Plan)
Developer: Implement validation, write tests
  ↓ (Code + Tests)
Tester: Validate & approve ✅
  ↓
Feature complete and production-ready
```

### Example 2: Issues Requiring Iteration

```
PO: "Add time entry validation"
  ↓
Architect: Design validation module
  ↓
Developer: Implement validation, write tests
  ↓
Tester: Coverage issue detected ❌
  ↓
Developer: Add missing tests, increase coverage
  ↓
Tester: Validate & approve ✅
  ↓
Feature complete
```

## 🔗 Related Files

- `.github/agents/product-owner.agent.md` - Product Owner Agent configuration
- `.github/agents/architect.agent.md` - Architect Agent configuration
- `.github/agents/developer.agent.md` - Developer Agent configuration
- `.github/agents/tester.agent.md` - Tester & Validator Agent configuration
- `README.md` - Project documentation
- `doc/ARCHITECTURE.md` - System architecture
- `doc/CONTRIBUTING.md` - Contributing guidelines & Git workflow (see "Phase 0: Agent-Based Feature Development")
- `doc/AGENTS_WORKFLOW.md` - This file
- `doc/TESTING.md` - Testing documentation

## 🚨 Troubleshooting

### Agent Not Responding
- Verify agent file exists in `.github/agents/`
- Check YAML frontmatter is valid
- Ensure agent name matches references

### Workflow Stalling
- Check output format matches handoff prompt
- Verify all required context is included
- Review constraints for agent handoff

### Quality Issues
- Review against project documentation references
- Check if agent is following output format
- Verify tools are available to agent

---

**Last Updated:** 2026-04-21
**Version:** 1.0
**Status:** ✅ Production Ready
