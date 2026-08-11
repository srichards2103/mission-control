## 🎯 The Challenge

Space organisations need to plan complex missions requiring specific crew capabilities. Crew assignment is currently manual and error-prone — leads spend hours cross-referencing skill profiles, availability calendars, and existing commitments. Multiple organisations will use this platform, each with different crew sizes, skill taxonomies, and approval processes.

**Mission Control** is a B2B platform that helps organisations manage missions and intelligently assign crew based on skills, availability, and workload. Your task is to design and build it.

You have broad latitude over the product design, data model, and technical architecture. We're looking for a solution you'd be comfortable putting in front of a customer.

**Minimum scope:** Multi-tenant auth with roles, a mission lifecycle with approval workflow, a crew management system with skill profiles, an auto-matching engine, and a dashboard with meaningful org-level metrics.

### What We Expect

A working product that demonstrates senior-level judgment across the entire stack. The data model should be well-considered. The matching algorithm should show real thought about the problem space. The UI should feel like a product, not a prototype. The code should be structured for a team to work in, not just for a demo to run.

---

## 🌍 The Domain

Mission Control is a **multi-tenant B2B platform** for space organisations. Here's the world you're building for:

- **Organisations** are your tenants — space agencies, research labs, private companies. All data is strictly scoped to an organisation. Data must never leak across tenants.
- **Crew Members** belong to an organisation. They have skill profiles, availability, and assignment history. How you model skills and proficiency is up to you.
- **Missions** belong to an organisation. They have requirements, timelines, and a lifecycle that includes some form of approval before going active. How you design the lifecycle and its transitions is a design decision we're interested in.
- **Assignments** connect crew to missions. The platform should include an **auto-matching engine** that intelligently suggests crew for missions based on skills, availability, and constraints. The sophistication of this algorithm is part of what we're evaluating.

### Roles

The platform has three roles. How you implement access control is your call. A local auth mechanism is fine (e.g. JWT-based login with seeded users, or a role-switching dev interface) — we care about tenant isolation and RBAC enforcement, not whether you've wired up a hosted identity provider. The intent is:

- **Directors** run the organisation. They manage settings, approve missions, and have broad visibility.
- **Mission Leads** plan and manage missions. They define requirements, run the matcher, and submit missions for approval. They should not be able to approve their own missions.
- **Crew Members** manage their own profiles, availability, and respond to assignments. They have limited visibility into the broader organisation.

---

## 📝 About the AI Transcripts

The transcripts are a **first-class evaluation artifact** — as important as the code itself. We're as interested in how you work with your AI tool as what you produce.

Don't edit them. We want to see your real process, including dead ends and mistakes.
