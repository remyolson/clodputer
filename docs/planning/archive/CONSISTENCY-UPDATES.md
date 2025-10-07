# Consistency Updates Required

**Date**: October 7, 2025
**Purpose**: Document all inconsistencies found and corrections needed

---

## Issues Found

### 1. README.md - Outdated Status

**Current**:
```markdown
**⏸️ Waiting on Your Input**:
- Review [Decision Matrix](04-decision-matrix.md)
- Answer key questions about priorities and preferences
```

**Should Be**:
```markdown
**✅ All Decisions Made**:
- Architecture: On-demand spawning with sequential queue
- UI: Menu bar icon with terminal dashboard
- Installation: Auto-updates CLAUDE.md with safety features
- Ready for engineer review
```

---

### 2. README.md - Missing New Documents

**Current**: Lists only documents 0-4

**Should Include**:
- 05-finalized-specification.md
- 06-user-experience.md
- 07-menu-bar-ui.md
- 08-installation-and-integration.md
- 09-safety-features.md
- 00-START-HERE.md

---

###3. README.md - Outdated Questions Section

**Current**:
```markdown
## Key Questions for You
1. Does the MVP scope match your needs?
2. Which use case will you test first?
...
```

**Should Be**: Remove this section entirely - all questions answered

---

### 4. SUMMARY.md - Missing Menu Bar UI

**Current**: Lists 8 documents, missing recent additions

**Should Include**:
- 06-user-experience.md
- 07-menu-bar-ui.md
- 08-installation-and-integration.md
- 09-safety-features.md
- 00-START-HERE.md
- CLAUDE-MD-ADDITION.md

---

### 5. SUMMARY.md - Outdated "What's Next"

**Current**:
```markdown
## What's Next
### Immediate Next Step
**Create new repository and start building!**
```

**Should Be**:
```markdown
## What's Next
### Immediate Next Step
**Share planning docs with engineer friend for review**

After review:
1. Incorporate feedback
2. Resolve any open questions
3. Then create repository and start building
```

---

### 6. SUMMARY.md - Missing Key Decisions

**Current**: Lists basic decisions but missing:

**Should Add**:
- ✅ **Menu bar icon** with terminal dashboard
- ✅ **CLAUDE.md auto-update** with multiple safety layers
- ✅ **Homebrew distribution**

---

### 7. 04-decision-matrix.md - Outdated (Still Has Questions)

**Current**: Full of open questions awaiting user input

**Should Be**: Updated with "Decisions Finalized" section showing all answers

**Note**: This file might be useful to KEEP AS-IS for historical reference of the decision process. The engineer can see what trade-offs were considered.

**Recommendation**: Add header note:
```markdown
# Decision Matrix & Key Questions

**NOTE**: This document shows the original decision-making process.
**All decisions have been made - see [05-finalized-specification.md](05-finalized-specification.md)**

For historical reference and to understand trade-offs considered.
```

---

## Corrections to Make

### Update README.md

1. Change status from "Waiting on Input" to "Planning Complete"
2. Add all new documents to index
3. Remove "Key Questions for You" section
4. Update "Current Status" section
5. Update "What Happens Next" to reflect engineer review phase

### Update SUMMARY.md

1. Add menu bar UI to key decisions
2. Add all new documents (6-9, 00-START-HERE)
3. Update documentation count (14 docs, not 8)
4. Update "What's Next" to reflect engineer review
5. Update file size totals

### Update 04-decision-matrix.md

1. Add header note clarifying this is historical
2. Point to 05-finalized-specification.md for actual decisions

### Verify Cross-References

All documents should reference:
- 00-START-HERE.md as entry point for engineers
- 05-finalized-specification.md for final decisions
- 09-safety-features.md for safety critical items

---

## Verification Checklist

After updates:
- [ ] README.md status is "Planning Complete - Ready for Review"
- [ ] README.md lists all 14 documents
- [ ] README.md has no open questions
- [ ] SUMMARY.md includes menu bar UI in decisions
- [ ] SUMMARY.md lists all 14 documents
- [ ] SUMMARY.md references engineer review as next step
- [ ] 04-decision-matrix.md has clarifying header
- [ ] All cross-references work correctly
- [ ] No document claims "waiting for input"
- [ ] All documents reference 00-START-HERE.md as engineer entry point
