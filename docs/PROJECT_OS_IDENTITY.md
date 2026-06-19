# Project OS Identity

Authority without identity is incomplete.

Project OS now has two orthogonal graphs:

```text
Execution Graph:
Project -> Project Run -> Event Record -> Causality

Governance Graph:
Identity -> Role -> Authority -> Action
```

The execution graph answers:

```text
What happened?
Why did it happen?
```

The governance graph answers:

```text
Who acted?
Who was allowed to act?
Who is accountable?
```

This document defines the identity doctrine for Project OS. It does not implement
login screens, authentication middleware, cryptographic signatures, or user
accounts. It defines the identity layer that authority depends on.

## Doctrine

```text
No authority without identity.
No action without attribution.
No approval without an accountable actor.
No delegation without identifiable delegator and delegate.
```

Related doctrines:

```text
No direct power. Only granted power.
No state change without authority.
No authority without accountability.
No event may create an illegal state transition.
Evidence first. Behavior second.
No scheduling without causality.
```

Lifecycle doctrine lives in `PROJECT_OS_STATE_MACHINE.md`.

## Identity is not authentication

Identity asks:

```text
Who or what is this actor in Project OS records?
```

Authentication asks:

```text
How do we prove the actor is who they claim to be?
```

Project OS needs identity doctrine before authentication plumbing. A local
single-user phone workflow may start with simple identities, but the architecture
must still record who acted. Otherwise every future audit trail becomes:

```text
somebody did something somewhere, probably
```

Very official. Very useless.

## Identity object

An **Identity** is the stable actor reference used in Project OS governance and
event records.

Minimum conceptual fields:

```text
identity_id
identity_type
label
status
created_at
```

Future implementations may add:

```text
authentication binding
public key
provider account link
device binding
human contact route
agent definition reference
revocation metadata
```

Those are implementation details. The constitutional rule is that actions must
be attributable to an identity.

## Identity types

### Human Identity

A human identity represents a person accountable for decisions.

Examples:

```text
local_owner:kvandre12
operator:phone_user
maintainer:repo_admin
```

Human identities may hold Owner, Maintainer, Operator, or Observer roles.

### Agent Identity

An agent identity represents a worker actor.

Examples:

```text
agent:code-puppy-26c058
agent:planning-agent
agent:browser-agent
```

Agent identities may receive scoped authority through leases or delegation. They
must not become Project Owners by accident, vibes, or YAML goblinry.

### System Identity

A system identity represents Project OS services.

Examples:

```text
system:project_runtime
system:run_scheduler
system:event_queue
system:bridge_grants
```

System identities may emit records for automated behavior, but system identity is
not sovereign authority. A scheduler action still needs authority policy and a
causal trigger.

### External Identity

An external identity represents an actor outside the local Project OS boundary.

Examples:

```text
github:kvandre12-commits
chatgpt_connector:robinhood
android:device_owner
```

External identities should be linked, not blindly trusted. Linkage is attribution
first; authentication strength can improve later.

## Identity, Role, Authority, Capability

These layers must stay separate.

```text
Identity   = who/what the actor is
Role       = relationship to a Project or object
Authority  = what state changes the actor may perform
Capability = what tools or bridges the actor can technically use
Action     = what the actor actually did
```

Example:

```text
Identity:   agent:code-puppy-26c058
Role:       Agent on run-android-os-001
Authority:  checkpoint leased run
Capability: file write + shell command
Action:     updated docs and recorded event
```

A capability without authority is not permission. Authority without identity is
not accountable. An action without attribution is evidence with a hole in it.

## Attribution

Every state-changing action should be attributable.

A future action record should answer:

```text
actor_identity_id
actor_role
requested_action
target_object_type
target_object_id
authority_basis
capability_used
resulting_event_id
timestamp
```

Event Records already have `source`, which is the first accountability hook. The
future identity model should evolve this into structured actor attribution.

## Identity and Event Records

Event Records should eventually distinguish:

```text
source system
actor identity
authority role
authority basis
```

Example:

```text
source_system: system:project_runtime
actor_identity: agent:code-puppy-26c058
authority_role: Agent
authority_basis: leased_run:run-android-os-001
event_type: project_run_checkpointed
```

This makes causality explain both what happened and who was allowed to make it
happen.

## Identity and approvals

Approval must name the approver identity.

```text
approval_requested
  requested_by: agent:code-puppy-26c058
  target: run-android-os-001

approval_granted
  approved_by: human:local_owner
  authority_role: Project Owner
```

An agent must not approve its own privileged request. A scheduler must not
approve its own blocked action. A system identity may route approval; it must not
magically become the approver. Nice try, tiny robot bureaucracy.

## Identity and delegation

Delegation requires two identities:

```text
delegator_identity_id
delegate_identity_id
```

Delegation records should include:

```text
scope
actions
object boundary
issued_at
expires_at
revoked_at
resulting_event_id
```

Delegation cannot exceed the delegator's authority. If a Maintainer cannot grant
Project ownership, they cannot delegate Project ownership to an agent wearing a
fake mustache.

## Identity and Agent Leases

An Agent Lease binds an Agent Identity to a Project Run for scoped execution.

A lease should eventually record:

```text
lease_id
run_id
agent_identity_id
issued_by_identity_id
authority_basis
granted_actions
granted_capabilities
issued_at
expires_at
revoked_at
```

The lease is the bridge between governance and execution:

```text
Identity -> Role -> Authority -> Lease -> Project Run -> Action -> Event Record
```

## Identity and the Scheduler

The scheduler should have a system identity, but not owner authority.

Scheduler records should answer:

```text
which system identity acted?
which policy authorized the action?
which Event Record triggered it?
which identity receives the lease or wakeup?
which resulting Event Record proves it?
```

A scheduler may execute policy. It must not create authority out of thin air.
That would be less an OS and more a haunted spreadsheet.

## Identity status

Identities should have lifecycle state.

Suggested states:

```text
active
suspended
revoked
archived
```

Implications:

- suspended identities cannot receive new authority
- revoked identities cannot act
- archived identities remain visible for audit history
- historical Event Records must not lose attribution when an identity is revoked

Do not delete identity history just because an actor can no longer act. Audit
trails dislike amnesia.

## Single-user mode

In local single-user mode, the same human may operationally be:

```text
Project Owner
Project Maintainer
Operator
Observer
```

That is fine. The identity model should still preserve the conceptual difference
between identity and role.

```text
Identity: human:local_owner
Roles: Owner, Maintainer, Operator
```

Collapsing roles for convenience is acceptable. Erasing the distinction from the
architecture is not.

## Constitutional invariants

```text
Every authority-bearing action has an actor identity.
Every approval has an approver identity.
Every delegation has delegator and delegate identities.
Every Agent Lease names the leased agent identity and issuer identity.
Every system action is attributable to a system identity.
Revoked identities remain available for historical attribution.
Identity is separate from Role, Authority, Capability, and Action.
```

## Implementation details

These are not constitutional:

```text
string IDs vs UUIDs
local config vs database
single identity file vs normalized tables
exact identity_id format
passwords vs device binding vs OAuth vs public keys
whether humans and agents share one table
whether identity is synced across devices
```

Do not make the first storage format into a religion. We already have enough
religions; most of them have YAML.

## Creation-time validation targets

Future write paths should validate:

| Action | Identity validation |
|---|---|
| Create Project | creator identity exists and can become Owner |
| Assign Role | assigner identity has authority to assign that role |
| Change Objective | actor identity has authority for the Project/Objective |
| Complete Work Item | actor identity has delegated or role authority |
| Record Event | source and actor identity are attributable |
| Grant Approval | approver identity has approval authority and is not self-approving |
| Delegate Authority | delegator and delegate identities exist; scope is not wider than delegator authority |
| Allocate Lease | issuer and agent identities exist; issuer has lease authority |
| Wake Run | scheduler/system identity, policy, and triggering Event Record are recorded |

## Non-goals

This document does not implement:

```text
login
authentication
authorization middleware
identity storage
role storage
passwords
OAuth
public-key signatures
multi-user sync
approval queue
scheduler
agent lease allocation
```

It defines the attribution layer so authority has someone to belong to.
