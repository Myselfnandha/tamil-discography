---
description: Create new application command. Triggers App Builder skill and starts interactive dialogue with user.
---

# /create - Create Application

$ARGUMENTS

---

## Task

This command starts a new application creation process.

### Steps:

1. **Request Analysis & Socratic Clarification**
   - Understand the target application requirements and user expectations
   - Clarify any ambiguous architecture or tech stack choices with the user upfront

2. **Architecture & File Planning**
   - Determine tech stack (stdlib/minimal dependencies first per YAGNI)
   - Outline directory structure, models, and core API endpoints
   - Present concise implementation plan for user alignment

3. **Autonomous Implementation**
   - Build models, backend, and responsive frontend
   - Apply curated design aesthetics (Inter/Outfit fonts, modern dark/light slate palette)
   - Verify functionality empirically with tests and linters

4. **Live Verification & Preview**
   - Launch preview server with `python .agents/scripts/auto_preview.py` or native dev command
   - Present local URL to user

---

## Usage Examples

```
/create blog site
/create e-commerce app with product listing and cart
/create todo app
/create Instagram clone
/create crm system with customer management
```

---

## Before Starting

If request is unclear, ask these questions:
- What type of application?
- What are the basic features?
- Who will use it?

Use defaults, add details later.
