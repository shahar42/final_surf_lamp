# CLAUDE CODE - Documentation Assignment

## EXCLUSIVE FILE OWNERSHIP
**⚠️ CRITICAL**: Only work on files in this list. Do not modify any files assigned to Gemini.

### Your Files:
1. `README.md` (main project)
2. `SYSTEM_DOCUMENTATION.md`
3. `database_schema.txt`
4. `database_schema_v2.txt`
5. `arduino_architecture_schema.txt`
6. `surf-lamp-processor/README.md`

## TASK OVERVIEW

### Primary Goal: Core System Documentation & Architecture
Transform the main project documentation into a comprehensive, authoritative reference that serves as the single source of truth for the Surf Lamp system.

## SPECIFIC TASKS

### 1. README.md Consolidation (Priority 1)

**Current State**: Already well-structured but needs enhancement
**Goal**: Comprehensive main documentation

**Actions**:
- **Merge relevant sections** from SYSTEM_DOCUMENTATION.md to avoid duplication
- **Standardize timing intervals** (fix 20min vs 30min inconsistencies)
- **Add missing sections**:
  - Advanced troubleshooting procedures
  - Performance monitoring and optimization
  - Development workflow and contribution guidelines
  - Known limitations and future roadmap
- **Enhance architecture overview** with clearer component relationships
- **Improve quick start** with environment verification steps

### 2. SYSTEM_DOCUMENTATION.md Refinement

**Current State**: Detailed but overlaps with README.md
**Goal**: Technical deep-dive complement to README

**Actions**:
- **Remove sections** that duplicate README content
- **Focus on technical details**:
  - Detailed data flow diagrams
  - Database transaction patterns
  - Error handling and retry logic
  - Security implementation details
  - Performance characteristics and bottlenecks
- **Add development-focused content**:
  - Code architecture patterns
  - Testing strategies
  - Debugging procedures
  - Extension points for new features

### 3. Database Schema Updates

**Files**: `database_schema.txt`, `database_schema_v2.txt`, `arduino_architecture_schema.txt`

**Actions**:
- **Audit current schemas** against actual database implementation
- **Update ASCII diagrams** with any missing relationships
- **Add detailed field descriptions** and data types
- **Document schema migration procedures**
- **Create consolidated schema reference** if v2 supersedes original
- **Enhance Arduino architecture schema** with current implementation details

### 4. Background Processor Documentation

**File**: `surf-lamp-processor/README.md`

**Actions**:
- **Create comprehensive setup guide** for development and production
- **Document configuration options** and environment variables
- **Add monitoring and logging procedures**
- **Include performance tuning guidelines**
- **Add API rate limiting and error handling details**

## QUALITY STANDARDS

### Technical Accuracy:
- Verify all timing intervals against actual code
- Cross-reference database schema with implementation
- Validate API endpoints and response formats
- Test setup procedures on clean environment

### Documentation Structure:
- Clear hierarchy with logical flow
- Consistent terminology throughout
- Comprehensive cross-references
- Actionable troubleshooting steps

### Completeness:
- Cover all major use cases and workflows
- Include edge cases and error conditions
- Provide examples for complex procedures
- Address different skill levels (beginner to advanced)

## COORDINATION RULES

### Start Immediately:
- Begin with README.md consolidation
- Work on SYSTEM_DOCUMENTATION.md in parallel
- Complete database schema updates independently

### Reference Points for Gemini:
- Ensure technical specifications are accurate for Arduino team
- Provide clear API contracts for integration work
- Maintain consistent terminology for cross-references

### Communication:
- Use commit prefix `[CLAUDE]` for all changes
- Mark files as "IN PROGRESS" in commit messages
- Announce completion of major sections

## SUCCESS CRITERIA

### README.md:
- Single comprehensive entry point for the project
- Developers can understand architecture and get started quickly
- Clear deployment procedures for production environments
- Comprehensive troubleshooting covers 90% of common issues

### SYSTEM_DOCUMENTATION.md:
- Technical deep-dive that complements README
- Developers can extend and modify the system confidently
- Security and performance considerations are well-documented
- Integration points are clearly defined

### Schema Documentation:
- Database design is fully documented and up-to-date
- Schema migration procedures are clear
- Relationships and constraints are properly explained

## DELIVERABLES CHECKLIST

- [ ] README.md (enhanced and consolidated)
- [ ] SYSTEM_DOCUMENTATION.md (refined technical reference)
- [ ] database_schema.txt (updated and verified)
- [ ] database_schema_v2.txt (reviewed and consolidated if needed)
- [ ] arduino_architecture_schema.txt (enhanced with current details)
- [ ] surf-lamp-processor/README.md (comprehensive setup guide)

## HANDOFF PREPARATION

### For Gemini Integration:
- Ensure API specifications are accurate and complete
- Provide clear technical references for Arduino documentation
- Maintain consistent terminology for cross-linking
- Complete core technical docs before Gemini starts referencing them

## FINAL INTEGRATION

After Gemini completes Arduino documentation:
1. Add cross-references to Arduino setup procedures
2. Link to hardware requirements and troubleshooting
3. Ensure terminology consistency across all documentation
4. Create unified navigation structure

**Focus**: Authoritative technical reference that enables confident development, deployment, and maintenance of the Surf Lamp system.