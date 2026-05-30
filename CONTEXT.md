# Vroom HR

Vroom HR (Vietnamese Recruit-Onboard-Operate-Manage) is an open-source,
self-hosted HR management platform for Vietnamese enterprises. Each company
runs its own deployment (its own database and server). One deployment serves
exactly one company. This glossary fixes the canonical meaning of domain terms
so the team uses one word per concept across specs, code, and docs.

## Language

**Organization**:
The single company that owns a given deployment. It is a singleton — there is
exactly one Organization per running instance. Holds company-level settings
(name, tax code, timezone, holidays). It is NOT a data-isolation boundary,
because a deployment never contains more than one company.
_Avoid_: Company, Tenant, Account, Client

**Tenant**:
A legacy term from the Policy Engine, where `tenant_id` was designed as a
multi-company isolation key. In the self-hosted model there is only one
company per deployment, so `tenant_id` is effectively a constant. Treat any
existing `tenant_id` as an implementation detail to be frozen or removed, not
as a live multi-tenancy concept.
_Avoid_: using Tenant as if multiple companies share one deployment

**HR**:
An administrator role. Manages employees, policies, schedules, and approvals
for the Organization. Maps to the existing `admin` role.
_Avoid_: Manager (a manager is a separate approval concept), Administrator

**Employee**:
A person with an employment record in the system. An Employee is created at the
moment a Candidate is accepted, starting **inactive** (`is_active = false`,
onboarding in progress). When onboarding completes, the Employee becomes
**active** (`is_active = true`). Boundary: Candidate = not yet accepted;
inactive Employee = accepted, onboarding; active Employee = onboarding done.
Active Employees use the self-service side of the system.
_Avoid_: User (User is the auth-account concept; an Employee is the HR concept)

## AI Capabilities

The system has three distinct AI concepts. They are NOT the same thing and must
not be collapsed under the umbrella term "AI Agent".

**AI Automation**:
Background AI tasks that run on an event, with no conversation: email intent
classification (cv/partner/event/internal/other) and CV parsing into structured
data. Already implemented in the recruitment module. This is a pipeline, not an
agent.
_Avoid_: calling this "the AI Agent"

**AI Assistant**:
A conversational chatbot for HR (the admin role). It can READ recruitment and
onboarding data (candidate counts by status, parsed CV summaries, interview
schedules, onboarding progress) and DRAFT actions for HR (e.g. compose an
interview-invitation or congratulations email), but it never writes to the
database on its own — HR confirms every write (human-in-the-loop). Employee-side
assistant is a future extension, deferred with the attendance/leave modules.
_Avoid_: Chatbot (too generic), Agent (implies autonomous writes)

**AI Agent (autonomous)**:
A hypothetical future capability where AI decides and executes write actions on
its own. Explicitly out of scope — recorded only as a future direction.
_Avoid_: using "Agent" to describe the current Assistant, which is not autonomous

## Recruitment & Onboarding

**Candidate**:
A person being considered for employment, created (auto or manually) from a
parsed CV. Moves through a pipeline: new → reviewing → interview*scheduled →
accepted/rejected/archived. A Candidate is NOT yet an Employee.
\_Avoid*: Applicant, Employee (an Employee is post-onboarding)

**Backbone Flow**:
The project's single core workflow: incoming email → AI intent classification →
CV parsing → Candidate → HR review → interview scheduling → accept →
congratulations email → onboarding → Employee. This is what the project is
built around; everything else is secondary or shelved.
_Avoid_: Pipeline (pipeline refers specifically to the candidate status machine)

**Onboarding**:
A checklist-driven process that turns an accepted Candidate into an active
Employee. Triggered by the candidate "accepted" event. An OnboardingProcess
holds a list of tasks (e.g. sign contract, submit documents, assign
department/position, set start date); HR completes each task, and when all are
done the Candidate becomes an active Employee. The currently missing link in the
backbone.
_Avoid_: Promotion, Hiring

**Onboarding Task**:
A single item in an OnboardingProcess checklist, with a status (pending/done).
_Avoid_: Step, Stage

## AI Assistant Internals

**Tool**:
A typed function the AI Assistant can invoke. There are exactly two kinds, and
no others: Read-Tool and Draft-Tool. The LLM is never given a tool that writes
to the database — that safety boundary is structural, not a convention.
_Avoid_: Function (too generic), Plugin, Skill

**Read-Tool**:
A tool that executes a real read against existing services and returns live data
(e.g. count candidates by status, get a candidate, list the review queue). Safe
to call freely.
_Avoid_: Query (reserved for the command/query layer)

**Draft-Tool**:
A tool that does NOT execute a write. It returns a structured proposal — an
action type, its parameters, and a human-readable preview (e.g. a composed
interview-invitation email). The LLM can only ever propose; it cannot act.
_Avoid_: Write-tool, Action-tool

**Draft Action**:
The structured proposal returned by a Draft-Tool. HR reviews it and, on confirm,
the frontend calls the existing real write endpoint directly (not via the LLM).
This is the mechanism that keeps the Assistant human-in-the-loop.
_Avoid_: Auto-action, Command
