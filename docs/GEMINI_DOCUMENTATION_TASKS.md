# GEMINI CLI - Documentation Assignment

## EXCLUSIVE FILE OWNERSHIP
**⚠️ CRITICAL**: Only work on files in this list. Do not modify any files assigned to Claude Code.

### Your Files:
1. `arduino/README.md`
2. `arduino/Arduino_Surf_Lamp_Logic.md`
3. `arduino/SHIPPING_PREPARATION.md`
4. `surf-lamp-processor/arduino_payload_documentation.md`
5. `web_and_database/README.md`
6. `discovery-config/README.md`

## TASK OVERVIEW

### Primary Goal: Arduino & User-Facing Documentation
Transform Arduino documentation into comprehensive, production-ready guides for developers, manufacturers, and end users.

## SPECIFIC TASKS

### 1. Arduino Documentation Suite (`arduino/` folder)

**Consolidate and enhance:**
- **README.md**: Master Arduino setup guide
  - Hardware requirements and wiring diagrams
  - Development environment setup (Arduino IDE/PlatformIO)
  - Library dependencies and installation
  - Compilation and flashing instructions
  - Troubleshooting common development issues

- **Arduino_Surf_Lamp_Logic.md**: Device behavior reference
  - LED pattern documentation with visual examples
  - WiFi configuration process (step-by-step)
  - API endpoint behavior and responses
  - Status LED meaning reference table
  - Error codes and recovery procedures

- **SHIPPING_PREPARATION.md**: Production guide
  - Pre-shipping quality assurance checklist
  - Firmware modification procedures for production
  - Testing protocols for manufactured units
  - Customer setup instruction templates
  - Warranty and support considerations

### 2. API Documentation (`surf-lamp-processor/`)

**arduino_payload_documentation.md**:
- Standardize JSON payload format
- Add request/response examples
- Document error conditions and handling
- Include API versioning information
- Add curl examples for testing

### 3. Web Application Setup (`web_and_database/`)

**README.md**:
- Installation and configuration guide
- Environment setup (Python, PostgreSQL, Redis)
- Development vs production configurations
- Security setup and best practices
- Deployment procedures

### 4. Configuration Management (`discovery-config/`)

**README.md**:
- GitHub Pages deployment process
- Configuration file format documentation
- Update procedures for server discovery
- Backup and rollback strategies

## QUALITY STANDARDS

### Documentation Requirements:
- **Clear step-by-step instructions**
- **Copy-pasteable code blocks**
- **Troubleshooting sections for each major process**
- **Prerequisites clearly stated**
- **Platform-specific instructions where needed**

### Target Audiences:
- **Developers**: Technical implementation details
- **Manufacturers**: Production and quality assurance
- **End Users**: Simple setup and troubleshooting
- **Support Teams**: Diagnostic and repair procedures

## COORDINATION RULES

### Before You Start:
1. Wait for Claude Code to complete `SYSTEM_DOCUMENTATION.md` changes
2. Check that `README.md` consolidation is finished
3. Reference completed Claude work for technical accuracy

### During Work:
- Use commit prefix `[GEMINI]` for all changes
- Mark files as "IN PROGRESS" in commit messages
- Do not reference or link to files being modified by Claude

### Communication:
- Announce completion of each major file
- Request technical clarification if needed
- Coordinate cross-references only after both sides complete core work

## SUCCESS CRITERIA

### Arduino Documentation:
- A developer can set up and compile firmware from scratch
- A manufacturer can prepare devices for shipping
- An end user can successfully configure their device
- Support teams can diagnose and resolve common issues

### API Documentation:
- Clear request/response formats
- Comprehensive error handling
- Testing procedures included

### Setup Guides:
- Environment setup works on fresh systems
- Configuration procedures are foolproof
- Deployment instructions are production-ready

## DELIVERABLES CHECKLIST

- [ ] Arduino README.md (comprehensive setup guide)
- [ ] Arduino_Surf_Lamp_Logic.md (enhanced behavior documentation)
- [ ] SHIPPING_PREPARATION.md (production-ready guide)
- [ ] arduino_payload_documentation.md (standardized API docs)
- [ ] web_and_database/README.md (setup and deployment guide)
- [ ] discovery-config/README.md (configuration management guide)

## FINAL REVIEW

After completing all files:
1. Cross-check references to Claude-modified files
2. Ensure consistency in terminology and formatting
3. Verify all code examples and procedures
4. Test setup instructions on fresh environment if possible

**Remember**: Focus on user experience and practical implementation. Make documentation that enables success, not just describes features.